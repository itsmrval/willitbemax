import httpx
import base64
import logging
import asyncio
import re
import os
import json
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
    def __init__(self, scheduler_client=None):
        self.base_url = "https://www.formula1.com"
        self.timeout = 30.0
        self.scheduler_client = scheduler_client
        self._driver_number_cache = {}

    def _fetch_driver_number_mapping(self, season: int) -> Dict[str, int]:
        if not self.scheduler_client:
            raise Exception("No scheduler client available for driver number lookup")

        cache_key = f"season_{season}"
        if cache_key in self._driver_number_cache:
            return self._driver_number_cache[cache_key]

        response = self.scheduler_client.get_seasons(year=season)

        if not response.data.seasons:
            raise Exception(f"No season data found for {season}")

        season_data = response.data.seasons[0]
        mapping = {}

        for standing in season_data.driver_standings:
            if standing.driver_code and standing.driver_number > 0:
                mapping[standing.driver_code] = standing.driver_number

        if not mapping:
            raise Exception(f"No driver standings found for season {season}")

        self._driver_number_cache[cache_key] = mapping
        logger.info(f"Loaded {len(mapping)} driver number mappings for season {season}")
        return mapping

    def _create_selenium_driver(self):
        selenium_url = os.getenv('SELENIUM_URL', 'http://localhost:4444')
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        return webdriver.Remote(command_executor=selenium_url, options=chrome_options)

    def _fetch_schedule_with_selenium(self, season: int) -> List[Dict]:
        driver = self._create_selenium_driver()
        try:
            driver.get(f"{self.base_url}/en/racing/{season}")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            WebDriverWait(driver, 20).until(lambda d: d.execute_script(f"""
                return document.querySelectorAll('a[href*="/racing/{season}/"]').length >= 24 &&
                       Array.from(document.querySelectorAll('a[href*="/racing/{season}/"]')).filter(card =>
                           card.textContent.match(/ROUND\\s+\\d+/i)).length >= 24;
            """))

            rounds_data = driver.execute_script(f"""
                const roundsMap = new Map();
                document.querySelectorAll('a[href*="/racing/{season}/"]').forEach(card => {{
                    const href = card.getAttribute('href') || '';
                    const roundMatch = card.textContent.match(/ROUND\\s+(\\d+)/i);
                    if (!roundMatch || !href.includes('/racing/{season}/') || (href.match(/\\//g) || []).length < 4) return;
                    const location = href.split('/').pop();
                    if (!location || location === '{season}' || roundsMap.has(parseInt(roundMatch[1]))) return;
                    roundsMap.set(parseInt(roundMatch[1]), {{
                        round_id: parseInt(roundMatch[1]),
                        location: location,
                        name: location.replace(/-/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase())
                    }});
                }});
                return Array.from(roundsMap.values());
            """)
            rounds_data.sort(key=lambda x: x['round_id'])
            return rounds_data
        finally:
            driver.quit()

    async def fetch_rounds_for_season(self, season: int, specific_round_id: int = None, force_live_session: str = None) -> List[Dict]:
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
                    round_data = await self._fetch_round_details(client, season, metadata, force_live_session)
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
                    name = re.sub(rf'\s*{season}$', '', data['name']).strip()
                    name = re.sub(r'^FORMULA\s+1\s+', '', name, flags=re.IGNORECASE)
                    return name
            except:
                pass
        return None

    async def _fetch_round_details(self, client: httpx.AsyncClient, season: int, metadata: Dict, force_live_session: str = None) -> Dict:
        url = f"{self.base_url}/en/racing/{season}/{metadata['location']}"
        html = await self._fetch_with_retry(client, url)
        soup = BeautifulSoup(html, 'html.parser')

        round_name = self._extract_round_name(soup, season)
        if round_name:
            metadata['name'] = round_name

        circuit = await self._extract_circuit_info(client, soup, season, metadata['location'])

        sessions = await self._extract_sessions(client, season, metadata['location'], soup, force_live_session)

        first_date, end_date = self._extract_weekend_dates(soup, season)

        if not metadata['name'] or not metadata['name'].strip():
            raise Exception("Round name is empty or invalid")

        if not circuit['name']:
            raise Exception(f"Circuit name missing: name={circuit['name']}")
        
        if not circuit['image_base64']:
            raise Exception(f"Circuit image missing for {circuit['name']}")

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

    async def _extract_circuit_info(self, client: httpx.AsyncClient, soup: BeautifulSoup, season: int, location: str) -> Dict:
        circuit = {
            'name': '',
            'laps': 0,
            'image_base64': ''
        }

        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if data.get('@type') != 'SportsEvent':
                    continue

                location_data = data.get('location', {})
                if not circuit['name'] and location_data.get('name'):
                    circuit['name'] = location_data['name']
            except:
                pass

        img = soup.select_one('img[src*="/track/"], img[src*="Circuit"], img[src*="circuit"], img[alt*="circuit"], img[alt*="Circuit"]')
        if img and img.get('src'):
            image_url = img['src']
            if not image_url.startswith('http'):
                image_url = self.base_url + image_url
            try:
                circuit['image_base64'] = await self._download_image_as_base64(client, image_url)
            except Exception as e:
                logger.error(f"Failed to download circuit image from {image_url}: {e}")
                raise Exception(f"Circuit image download failed: {e}")
        else:
            logger.error(f"No circuit image element found in HTML for {location}")
            raise Exception(f"No circuit image element found for {location}")

        dt_elem = soup.find('dt', text=re.compile(r'Number\s+of\s+Laps', re.IGNORECASE))
        if dt_elem:
            dd_elem = dt_elem.find_next_sibling('dd')
            if dd_elem:
                laps_text = dd_elem.get_text().strip()
                match = re.search(r'(\d+)', laps_text)
                if match:
                    circuit['laps'] = int(match.group(1))

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
        return 0, 0

    def _extract_all_session_dates_sync(self, season: int, location: str) -> Dict[str, int]:
        driver = self._create_selenium_driver()
        try:
            driver.get(f"{self.base_url}/en/racing/{season}/{location}")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "script"))
            )

            soup = BeautifulSoup(driver.page_source, 'lxml')
            session_dates = {}
            session_map = {
                'practice 1': 'practice_1',
                'practice 2': 'practice_2',
                'practice 3': 'practice_3',
                'qualifying': 'qualifying',
                'sprint qualifying': 'sprint_qualifying',
                'sprint': 'sprint',
                'race': 'race'
            }

            for script in soup.find_all('script'):
                if not script.string or '"@type":"SportsEvent"' not in script.string:
                    continue

                start = 0
                while True:
                    event_start = script.string.find('"@type":"SportsEvent"', start)
                    if event_start == -1:
                        break

                    brace_start = script.string.rfind('{', 0, event_start)
                    if brace_start == -1:
                        break

                    brace_count = 1
                    pos = brace_start + 1
                    while pos < len(script.string) and brace_count > 0:
                        if script.string[pos] == '{':
                            brace_count += 1
                        elif script.string[pos] == '}':
                            brace_count -= 1
                        pos += 1

                    if brace_count == 0:
                        try:
                            event_data = json.loads(script.string[brace_start:pos])
                            if not (event_data.get('@type') == 'SportsEvent' and event_data.get('name') and event_data.get('startDate')):
                                continue

                            name_lower = event_data['name'].lower()
                            session_type = self._detect_session_type(name_lower, session_map)

                            if session_type and session_type not in session_dates:
                                date_str = event_data['startDate'].replace('Z', '+00:00')
                                session_dates[session_type] = int(datetime.fromisoformat(date_str).timestamp())
                        except:
                            pass
                    start = event_start + 1
            return session_dates
        finally:
            driver.quit()

    def _detect_session_type(self, name_lower: str, session_map: Dict[str, str]) -> Optional[str]:
        for key, type_val in session_map.items():
            if key not in name_lower:
                continue

            if key == 'sprint' and 'qualifying' in name_lower:
                return 'sprint_qualifying'
            elif key == 'qualifying' and 'sprint' in name_lower:
                continue
            else:
                return type_val
        return None

    def _detect_live_session_from_html(self, soup: BeautifulSoup) -> Optional[str]:
        session_text_map = {
            'practice 1': 'practice_1',
            'practice 2': 'practice_2',
            'practice 3': 'practice_3',
            'qualifying': 'qualifying',
            'sprint qualifying': 'sprint_qualifying',
            'sprint': 'sprint',
            'race': 'race'
        }

        live_timing_elements = soup.find_all(text=re.compile(r'Live\s+Timing', re.IGNORECASE))
        if not live_timing_elements:
            return None

        for element in live_timing_elements:
            parent = element.parent
            while parent and parent.name != 'body':
                row_text = parent.get_text().lower()
                for session_text, session_type in session_text_map.items():
                    if session_text in row_text:
                        logger.info(f"Detected live session: {session_type}")
                        return session_type
                parent = parent.parent

        return None

    async def _extract_sessions(self, client: httpx.AsyncClient, season: int, location: str, soup: BeautifulSoup, force_live_session: str = None) -> List[Dict]:
        session_dates = await asyncio.to_thread(self._extract_all_session_dates_sync, season, location)
        logger.info(f"Extracted session dates for {location}: {list(session_dates.keys())}")
        result_links = soup.find_all('a', href=re.compile(rf'/results/{season}/races/\d+/[^/]+/(practice|qualifying|sprint|race)'))

        live_session_type = force_live_session if force_live_session else self._detect_live_session_from_html(soup)
        live_positions = []
        if live_session_type:
            logger.info(f"{'Forced' if force_live_session else 'Detected'} live session for {location}: {live_session_type}")
            live_positions = await self._fetch_live_positions_via_selenium(season)

        if not result_links:
            return [{
                'type': session_type,
                'date': date,
                'total_laps': 0,
                'current_lap': 0,
                'results': [],
                'is_live': session_type == live_session_type,
                'status': self._determine_session_status(date, session_type == live_session_type)
            } for session_type, date in session_dates.items()]

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

        for link in result_links:
            href = link.get('href', '')
            if not href or f'/results/{season}/' not in href:
                continue

            for path_key, session_type in session_type_map.items():
                if session_type in fetched_types:
                    continue
                if not (href.endswith(f'/{path_key}') or f'/{path_key}' in href):
                    continue

                try:
                    full_url = href if href.startswith('http') else self.base_url + href
                    session_date = session_dates.get(session_type, 0)
                    is_live = session_type == live_session_type
                    status = self._determine_session_status(session_date, is_live)

                    if is_live and live_positions:
                        logger.info(f"Using live positions for {session_type}")
                        results = self._convert_live_positions_to_results(live_positions)
                    else:
                        results = await asyncio.to_thread(self._fetch_session_results_sync, full_url)

                    sessions.append({
                        'type': session_type,
                        'date': session_date,
                        'total_laps': 0,
                        'current_lap': 0,
                        'results': results,
                        'is_live': is_live,
                        'status': status
                    })
                    fetched_types.add(session_type)
                    await asyncio.sleep(0.5)
                    break
                except Exception as e:
                    logger.error(f"Failed to fetch session {session_type}: {e}")
                    raise

        for session_type, date in session_dates.items():
            if session_type not in fetched_types:
                is_live = session_type == live_session_type
                results = []
                if is_live and live_positions:
                    results = self._convert_live_positions_to_results(live_positions)

                sessions.append({
                    'type': session_type,
                    'date': date,
                    'total_laps': 0,
                    'current_lap': 0,
                    'results': results,
                    'is_live': is_live,
                    'status': self._determine_session_status(date, is_live)
                })

        return sessions

    def _convert_live_positions_to_results(self, live_positions: List[Dict]) -> List[Dict]:
        if isinstance(live_positions, list):
            return sorted(live_positions, key=lambda x: x.get('position', 0))
        return []

    def _fetch_session_results_sync(self, url: str) -> List[Dict]:
        driver = self._create_selenium_driver()
        try:
            driver.get(url)
            WebDriverWait(driver, 20).until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "table tbody tr")) > 0)
            return self._parse_session_results(BeautifulSoup(driver.page_source, 'html.parser'))
        finally:
            driver.quit()

    def _parse_session_results(self, soup: BeautifulSoup) -> List[Dict]:
        table = soup.select_one('table')
        if not table:
            return []

        results = []
        for row in table.select('tbody tr'):
            cells = row.select('td')
            if len(cells) < 5:
                continue

            try:
                position_text = cells[0].text.strip()
                position_match = re.search(r'\d+', position_text)
                position = int(position_match.group()) if position_match else 0

                number_text = cells[1].text.strip()
                number_match = re.search(r'\d+', number_text)
                driver_number = int(number_match.group()) if number_match else 0

                driver_name_raw = cells[2].text.strip()
                code_match = re.search(r'[A-Z]{3}$', driver_name_raw)
                driver_code = code_match.group() if code_match else ''
                driver_name = re.sub(r'[A-Z]{3}$', '', driver_name_raw).strip() or driver_name_raw

                team = cells[3].text.strip()
                cell_4_text = cells[4].text.strip()
                is_race = cell_4_text.isdigit()

                if is_race and len(cells) > 5:
                    time = cells[5].text.strip()
                    laps = int(cell_4_text)
                else:
                    time = cell_4_text
                    laps = 0

                results.append({
                    'position': position,
                    'driver_number': driver_number,
                    'driver_name': driver_name,
                    'driver_code': driver_code,
                    'team': team,
                    'time': time,
                    'laps': laps
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

    async def _check_live_timing_static(self, client: httpx.AsyncClient) -> Optional[Dict]:
        try:
            url = "https://livetiming.formula1.com/static/SessionInfo.json"
            response = await client.get(url)

            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.debug(f"No live session found: {e}")
            return None

    def _scrape_live_timing_page_sync(self, season: int) -> List[Dict]:
        driver = self._create_selenium_driver()
        try:
            url = "https://www.formula1.com/en/timing/f1-live-lite"
            driver.get(url)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )

            import time
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver_number_mapping = self._fetch_driver_number_mapping(season)

            results = []
            table = soup.select_one('table')

            if table:
                rows = table.select('tbody tr')
                logger.info(f"Found {len(rows)} rows in live timing table")

                for row in rows:
                    cells = row.select('td')

                    position_match = re.search(r'\d+', cells[0].text.strip())
                    position = int(position_match.group())

                    driver_cell = cells[1]

                    first_name_elem = driver_cell.select_one('.driverName span.font-normal')
                    last_name_elem = driver_cell.select_one('.driverName span.uppercase')
                    team_elem = driver_cell.select_one('.text-grey-60')
                    code_elem = driver_cell.select_one('.font-formula.tablet\\:hidden')

                    first_name = first_name_elem.text.strip() if first_name_elem else ''
                    last_name = last_name_elem.text.strip() if last_name_elem else ''
                    driver_name = f"{first_name} {last_name}".strip()
                    team = team_elem.text.strip() if team_elem else ''
                    driver_code = code_elem.text.strip() if code_elem else ''

                    driver_number = 0
                    number_elem = driver_cell.select_one('[data-driver-number]')
                    if number_elem:
                        driver_number = int(number_elem.get('data-driver-number'))

                    if driver_number == 0:
                        if not driver_code:
                            raise Exception(f"Missing driver_code for position {position}, cannot lookup driver_number")
                        if driver_code not in driver_number_mapping:
                            raise Exception(f"Driver code '{driver_code}' not found in database for season {season}")
                        driver_number = driver_number_mapping[driver_code]
                        logger.info(f"Populated driver_number {driver_number} for {driver_code} from database")

                    time_val = cells[2].text.strip()

                    results.append({
                        'position': position,
                        'driver_number': driver_number,
                        'driver_name': driver_name,
                        'driver_code': driver_code,
                        'team': team,
                        'time': time_val,
                        'laps': 0
                    })

            return results
        finally:
            driver.quit()

    async def _fetch_live_positions_via_selenium(self, season: int) -> List[Dict]:
        return await asyncio.to_thread(self._scrape_live_timing_page_sync, season)

    def _determine_session_status(self, session_date: int, is_live: bool = False) -> str:
        if is_live:
            return "live"

        current_time = int(datetime.now().timestamp())
        session_duration = 7200

        if current_time < session_date:
            return "upcoming"
        elif current_time < session_date + session_duration:
            return "live"
        else:
            return "finished"