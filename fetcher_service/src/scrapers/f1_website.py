import httpx
import base64
import logging
import asyncio
import re
import os
import json
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class F1WebsiteClient:
    def __init__(self, ergast_client=None):
        self.base_url = "https://www.formula1.com"
        self.timeout = 30.0
        self.ergast = ergast_client

    def _create_selenium_driver(self):
        selenium_url = os.getenv('SELENIUM_URL', 'http://localhost:4444')
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        return webdriver.Remote(command_executor=selenium_url, options=chrome_options)

    def _fetch_schedule_with_selenium(self, season: int) -> List[Dict]:
        url = f"{self.base_url}/en/racing/{season}"
        driver = self._create_selenium_driver()

        try:
            logger.info(f"Fetching schedule page with Selenium: {url}")
            driver.get(url)

            def wait_for_all_rounds(driver):
                script = f"""
                const cards = document.querySelectorAll('a[href*="/racing/{season}/"]');
                const roundTexts = Array.from(cards).filter(card =>
                    card.textContent.match(/ROUND\\s+\\d+/i)
                );
                return roundTexts.length;
                """
                count = driver.execute_script(script)
                return count >= 24

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            WebDriverWait(driver, 20).until(wait_for_all_rounds)

            rounds_data = driver.execute_script(f"""
                const cards = document.querySelectorAll('a[href*="/racing/{season}/"]');
                const roundsMap = new Map();

                cards.forEach(card => {{
                    const href = card.getAttribute('href') || '';
                    const text = card.textContent;
                    const roundMatch = text.match(/ROUND\\s+(\\d+)/i);

                    if (!roundMatch) return;
                    if (!href.includes('/racing/{season}/') || (href.match(/\\//g) || []).length < 4) return;

                    const location = href.split('/').pop();
                    if (!location || location === '{season}') return;

                    const roundId = parseInt(roundMatch[1]);
                    if (roundsMap.has(roundId)) return;

                    const name = location.replace(/-/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase());

                    roundsMap.set(roundId, {{
                        round_id: roundId,
                        location: location,
                        name: name
                    }});
                }});

                return Array.from(roundsMap.values());
            """)

            rounds_data.sort(key=lambda x: x['round_id'])
            return rounds_data
        finally:
            driver.quit()

    async def fetch_rounds_for_season(self, season: int, specific_round_id: int = None) -> List[Dict]:
        rounds_metadata = await asyncio.to_thread(self._fetch_schedule_with_selenium, season)

        if specific_round_id is not None:
            rounds_metadata = [m for m in rounds_metadata if m['round_id'] == specific_round_id]
            if not rounds_metadata:
                logger.error(f"Round {specific_round_id} not found in season {season}")
                return []

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            all_rounds = []
            for metadata in rounds_metadata:
                try:
                    round_data = await self._fetch_round_details(client, season, metadata)
                    all_rounds.append(round_data)
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Failed to fetch round {metadata.get('name', 'Unknown')}: {e}")
                    return []

            return all_rounds

    def _extract_round_name(self, soup: BeautifulSoup, season: int) -> Optional[str]:
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'SportsEvent' and data.get('name'):
                    return re.sub(rf'\s*{season}$', '', data['name']).strip()
            except:
                pass
        return None

    async def _fetch_round_details(self, client: httpx.AsyncClient, season: int, metadata: Dict) -> Dict:
        url = f"{self.base_url}/en/racing/{season}/{metadata['location']}"
        html = await self._fetch_with_retry(client, url)
        soup = BeautifulSoup(html, 'html.parser')

        round_name = self._extract_round_name(soup, season)
        if round_name:
            metadata['name'] = round_name

        circuit = await self._extract_circuit_info(client, soup)

        if self.ergast:
            ergast_circuit = await self.ergast.fetch_circuit_for_round(season, metadata['round_id'])
            if ergast_circuit:
                circuit['lat'] = ergast_circuit.get('lat', '0')
                circuit['long'] = ergast_circuit.get('long', '0')
                if not circuit['locality'] and ergast_circuit.get('locality'):
                    circuit['locality'] = ergast_circuit['locality']
                if not circuit['country'] and ergast_circuit.get('country'):
                    circuit['country'] = ergast_circuit['country']

        sessions = await self._extract_sessions(client, season, metadata['location'], soup)

        first_date, end_date = self._extract_weekend_dates(soup, season)

        if not metadata['name'] or not metadata['name'].strip():
            raise Exception("Round name is empty or invalid")

        if not circuit['name'] or circuit['laps'] == 0:
            raise Exception(f"Circuit information incomplete: name={circuit['name']}, laps={circuit['laps']}")

        if circuit['lat'] == '0' or circuit['long'] == '0':
            raise Exception(f"Circuit coordinates missing: lat={circuit['lat']}, long={circuit['long']}")

        if not circuit['locality'] or not circuit['country']:
            raise Exception(f"Circuit location missing: locality={circuit['locality']}, country={circuit['country']}")

        if first_date == 0 or end_date == 0:
            raise Exception("Round dates incomplete")

        return {
            'round_id': metadata['round_id'],
            'name': metadata['name'],
            'season': season,
            'circuit': circuit,
            'first_date': first_date,
            'end_date': end_date,
            'sessions': sessions
        }

    async def _extract_circuit_info(self, client: httpx.AsyncClient, soup: BeautifulSoup) -> Dict:
        circuit = {'name': '', 'locality': '', 'country': '', 'lat': '0', 'long': '0', 'laps': 0, 'image_base64': ''}

        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'SportsEvent':
                    location = data.get('location', {})
                    if not circuit['name'] and location.get('name'):
                        circuit['name'] = location['name']

                    address = location.get('address', {})
                    if address.get('addressLocality'):
                        circuit['locality'] = address['addressLocality']
                    if address.get('addressCountry'):
                        circuit['country'] = address['addressCountry']

                    geo = location.get('geo', {})
                    if geo.get('latitude') and geo['latitude'] != 0:
                        circuit['lat'] = str(geo['latitude'])
                    if geo.get('longitude') and geo['longitude'] != 0:
                        circuit['long'] = str(geo['longitude'])
            except:
                pass

        if not circuit['name']:
            circuit_elem = soup.find(text=re.compile(r'Circuit', re.IGNORECASE))
            if circuit_elem:
                circuit['name'] = circuit_elem.strip()

        img = soup.select_one('img[src*="Circuit"], img[src*="circuit"], img[alt*="circuit"]')
        if img and img.get('src'):
            image_url = img['src'] if img['src'].startswith('http') else self.base_url + img['src']
            try:
                circuit['image_base64'] = await self._download_image_as_base64(client, image_url)
            except:
                pass

        dt_elem = soup.find('dt', text=re.compile(r'Number\s+of\s+Laps', re.IGNORECASE))
        if dt_elem and (dd_elem := dt_elem.find_next_sibling('dd')):
            if match := re.search(r'(\d+)', dd_elem.get_text().strip()):
                circuit['laps'] = int(match.group(1))

        if not circuit['name'] and not circuit['laps']:
            raise Exception("Failed to extract circuit information")

        return circuit

    async def _download_image_as_base64(self, client: httpx.AsyncClient, url: str) -> str:
        response = await client.get(url)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')

    def _extract_weekend_dates(self, soup: BeautifulSoup, season: int) -> tuple:
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'SportsEvent' and data.get('startDate') and data.get('endDate'):
                    start_dt = datetime.fromisoformat(data['startDate'].replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(data['endDate'].replace('Z', '+00:00'))
                    return int(start_dt.timestamp()), int(end_dt.timestamp())
            except:
                pass

        dates = []
        for elem in soup.find_all(text=re.compile(r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', re.IGNORECASE))[:5]:
            if match := re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', elem, re.IGNORECASE):
                day = int(match.group(1))
                month = datetime.strptime(match.group(2), '%b').month
                dates.append(int(datetime(season, month, day).timestamp()))

        if dates:
            dates.sort()
            return dates[0], dates[-1]
        return 0, 0

    def _extract_scheduled_sessions_sync(self, season: int, location: str) -> List[Dict]:
        driver = self._create_selenium_driver()
        try:
            logger.info(f"Fetching scheduled sessions: {self.base_url}/en/racing/{season}/{location}")
            driver.get(f"{self.base_url}/en/racing/{season}/{location}")
            time.sleep(5)

            soup = BeautifulSoup(driver.page_source, 'lxml')
            sessions = []
            session_map = {'practice 1': 'practice_1', 'practice 2': 'practice_2', 'practice 3': 'practice_3',
                          'qualifying': 'qualifying', 'sprint qualifying': 'sprint_qualifying', 'sprint': 'sprint', 'race': 'race'}

            for script in soup.find_all('script'):
                if not script.string or '"@type":"SportsEvent"' not in script.string:
                    continue

                start = 0
                while (event_start := script.string.find('"@type":"SportsEvent"', start)) != -1:
                    brace_start = script.string.rfind('{', 0, event_start)
                    if brace_start == -1:
                        break

                    brace_count, pos = 1, brace_start + 1
                    while pos < len(script.string) and brace_count > 0:
                        if script.string[pos] == '{':
                            brace_count += 1
                        elif script.string[pos] == '}':
                            brace_count -= 1
                        pos += 1

                    if brace_count == 0:
                        try:
                            event_data = json.loads(script.string[brace_start:pos])
                            if event_data.get('@type') == 'SportsEvent' and event_data.get('name') and event_data.get('startDate'):
                                name_lower = event_data['name'].lower()
                                session_type = None

                                for key, type_val in session_map.items():
                                    if key in name_lower:
                                        session_type = 'sprint_qualifying' if key == 'sprint' and 'qualifying' in name_lower else type_val if not (key == 'qualifying' and 'sprint' in name_lower) else None
                                        if session_type:
                                            break

                                if session_type:
                                    dt = datetime.fromisoformat(event_data['startDate'].replace('Z', '+00:00'))
                                    sessions.append({'type': session_type, 'date': int(dt.timestamp())})
                        except:
                            pass
                    start = event_start + 1

            logger.info(f"Found {len(sessions)} scheduled sessions for {location}")
            return [{'type': s['type'], 'date': s['date'], 'total_laps': 0, 'current_lap': 0, 'results': []} for s in sessions]
        finally:
            driver.quit()

    async def _extract_sessions(self, client: httpx.AsyncClient, season: int, location: str, soup: BeautifulSoup) -> List[Dict]:
        sessions = []
        fetched_types = set()

        session_type_map = {
            'practice/1': 'practice_1',
            'practice/2': 'practice_2',
            'practice/3': 'practice_3',
            'qualifying': 'qualifying',
            'sprint-qualifying': 'sprint_qualifying',
            'sprint': 'sprint',
            'race-result': 'race'
        }

        result_links = soup.find_all('a', href=re.compile(rf'/results/{season}/races/\d+/{location}'))

        for link in result_links:
            href = link.get('href', '')
            if not href:
                continue

            if f'/results/{season}/' not in href or f'/{location}/' not in href:
                continue

            for path_key, session_type in session_type_map.items():
                if session_type in fetched_types:
                    continue

                if href.endswith(f'/{path_key}') or f'/{path_key}' in href:
                    try:
                        full_url = self.base_url + href if not href.startswith('http') else href
                        session_data = await self._fetch_session_data(client, full_url, session_type, season)

                        if session_data['date'] == 0:
                            raise Exception(f"Failed to extract date for session {session_type}")

                        sessions.append(session_data)
                        fetched_types.add(session_type)
                        await asyncio.sleep(0.5)
                        break
                    except Exception as e:
                        logger.error(f"Failed to fetch session {session_type}: {e}")
                        raise

        if not sessions:
            logger.info(f"No result links found for {location}, fetching scheduled sessions")
            sessions = await asyncio.to_thread(self._extract_scheduled_sessions_sync, season, location)

        return sessions

    def _fetch_session_data_sync(self, url: str, session_type: str, season: int) -> Dict:
        driver = self._create_selenium_driver()

        try:
            logger.info(f"Fetching session data: {url}")
            driver.get(url)

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )

            def table_has_data(driver):
                rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
                return len(rows) > 0

            WebDriverWait(driver, 20).until(table_has_data)

            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            session_date = self._extract_session_date(soup, season)
            if session_date == 0:
                raise Exception(f"Failed to extract session date from {url}")

            results = self._parse_session_results(soup)
            if not results:
                raise Exception(f"Failed to extract session results from {url}")

            return {
                'type': session_type,
                'date': session_date,
                'total_laps': 0,
                'current_lap': 0,
                'results': results
            }
        finally:
            driver.quit()

    async def _fetch_session_data(self, client: httpx.AsyncClient, url: str, session_type: str, season: int) -> Dict:
        return await asyncio.to_thread(self._fetch_session_data_sync, url, session_type, season)

    def _extract_session_date(self, soup: BeautifulSoup, season: int) -> int:
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if data.get('@type') == 'SportsEvent' and data.get('startDate'):
                    return int(datetime.fromisoformat(data['startDate'].replace('Z', '+00:00')).timestamp())
            except:
                pass

        for elem in soup.find_all(text=re.compile(r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', re.IGNORECASE)):
            if match := re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', elem, re.IGNORECASE):
                if int(match.group(3)) == season:
                    day, month = int(match.group(1)), datetime.strptime(match.group(2), '%b').month
                    return int(datetime(season, month, day).timestamp())
        return 0

    def _parse_session_results(self, soup: BeautifulSoup) -> List[Dict]:
        if not (table := soup.select_one('table')):
            return []

        results = []
        for row in table.select('tbody tr'):
            cells = row.select('td')
            if len(cells) < 5:
                continue

            try:
                position = int(re.search(r'\d+', cells[0].text.strip()).group()) if re.search(r'\d+', cells[0].text.strip()) else 0
                driver_number = int(re.search(r'\d+', cells[1].text.strip()).group()) if re.search(r'\d+', cells[1].text.strip()) else 0

                driver_name_raw = cells[2].text.strip()
                driver_code = match.group() if (match := re.search(r'[A-Z]{3}$', driver_name_raw)) else ''
                driver_name = re.sub(r'[A-Z]{3}$', '', driver_name_raw).strip() or driver_name_raw

                team = cells[3].text.strip()
                cell_4_text = cells[4].text.strip()
                is_race = bool(re.match(r'^\d+$', cell_4_text))

                results.append({
                    'position': position,
                    'driver_number': driver_number,
                    'driver_name': driver_name,
                    'driver_code': driver_code,
                    'team': team,
                    'time': cells[5].text.strip() if is_race and len(cells) > 5 else cell_4_text,
                    'laps': int(cell_4_text) if is_race and cell_4_text.isdigit() else 0
                })
            except:
                continue
        return results

    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Retry {attempt + 1}/{max_retries} for {url}: {e}")
                await asyncio.sleep(wait_time)
