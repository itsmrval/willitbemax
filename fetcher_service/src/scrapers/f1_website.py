import httpx
import base64
import logging
import asyncio
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class F1WebsiteClient:
    def __init__(self, ergast_client=None):
        self.base_url = "https://www.formula1.com"
        self.timeout = 30.0
        self.ergast = ergast_client

    async def fetch_rounds_for_season(self, season: int, specific_round_id: int = None) -> List[Dict]:
        schedule_url = f"{self.base_url}/en/racing/{season}"

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            schedule_html = await self._fetch_with_retry(client, schedule_url)

            rounds_metadata = self._parse_schedule_page(schedule_html, season)

            if specific_round_id is not None:
                rounds_metadata = [m for m in rounds_metadata if m['round_id'] == specific_round_id]
                if not rounds_metadata:
                    logger.error(f"Round {specific_round_id} not found in season {season}")
                    return []

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

    def _parse_schedule_page(self, html: str, season: int) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        rounds = []

        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'SportsEvent':
                    name = data.get('name', '')
                    if name:
                        name = re.sub(r'ROUND\s*\d+\s*', '', name, flags=re.IGNORECASE).strip()
                        name = re.sub(r'Chequered\s*Flag\s*', '', name, flags=re.IGNORECASE).strip()
                        name = re.sub(r'\d{1,2}\s*-\s*\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', '', name, flags=re.IGNORECASE).strip()

                    location_data = data.get('location', {})
                    if isinstance(location_data, dict):
                        address = location_data.get('address', {})
                        locality = address.get('addressLocality', '').lower().replace(' ', '-')
                        if locality and name:
                            rounds.append({
                                'round_id': len(rounds),
                                'location': locality,
                                'name': name
                            })
                elif isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'SportsEvent':
                            name = item.get('name', '')
                            if name:
                                name = re.sub(r'ROUND\s*\d+\s*', '', name, flags=re.IGNORECASE).strip()
                                name = re.sub(r'Chequered\s*Flag\s*', '', name, flags=re.IGNORECASE).strip()
                                name = re.sub(r'\d{1,2}\s*-\s*\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', '', name, flags=re.IGNORECASE).strip()

                            location_data = item.get('location', {})
                            if isinstance(location_data, dict):
                                address = location_data.get('address', {})
                                locality = address.get('addressLocality', '').lower().replace(' ', '-')
                                if locality and name:
                                    rounds.append({
                                        'round_id': len(rounds),
                                        'location': locality,
                                        'name': name
                                    })
            except Exception as e:
                logger.debug(f"Failed to parse ld+json: {e}")
                pass

        if not rounds:
            article_cards = soup.select('a[href*="/racing/"]')
            for idx, card in enumerate(article_cards):
                href = card.get('href', '')
                if f'/racing/{season}/' in href and href.count('/') >= 4:
                    location = href.split('/')[-1]
                    if location and location != str(season):
                        name_elem = card.select_one('[class*="title"], [class*="name"], h2, h3, h4, h5, span')
                        name = name_elem.text.strip() if name_elem else f"Round {idx + 1}"
                        if name and not name.isdigit():
                            rounds.append({
                                'round_id': idx,
                                'location': location,
                                'name': name
                            })

        seen = set()
        unique_rounds = []
        for idx, r in enumerate(rounds):
            if r['location'] not in seen:
                seen.add(r['location'])
                r['round_id'] = idx
                unique_rounds.append(r)

        return unique_rounds

    def _extract_round_name(self, soup: BeautifulSoup, season: int) -> Optional[str]:
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'SportsEvent':
                    name = data.get('name', '')
                    if name:
                        name = re.sub(rf'\s*{season}$', '', name).strip()
                        return name
            except Exception as e:
                logger.debug(f"Failed to parse JSON-LD for round name: {e}")

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
            ergast_round = metadata['round_id'] + 1
            ergast_circuit = await self.ergast.fetch_circuit_for_round(season, ergast_round)
            if ergast_circuit:
                circuit['lat'] = ergast_circuit.get('lat', '0')
                circuit['long'] = ergast_circuit.get('long', '0')
                if not circuit['locality'] and ergast_circuit.get('locality'):
                    circuit['locality'] = ergast_circuit['locality']
                if not circuit['country'] and ergast_circuit.get('country'):
                    circuit['country'] = ergast_circuit['country']

        logger.info(f"Final circuit data: name={circuit['name']}, locality={circuit['locality']}, country={circuit['country']}, lat={circuit['lat']}, long={circuit['long']}, laps={circuit['laps']}")

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
        circuit = {
            'name': '',
            'locality': '',
            'country': '',
            'lat': '0',
            'long': '0',
            'laps': 0,
            'image_base64': ''
        }

        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'SportsEvent':
                    location = data.get('location', {})
                    if isinstance(location, dict):
                        name = location.get('name', '')
                        if name and not circuit['name']:
                            circuit['name'] = name

                        address = location.get('address', {})
                        if isinstance(address, dict):
                            locality = address.get('addressLocality', '')
                            country = address.get('addressCountry', '')
                            if locality:
                                circuit['locality'] = locality
                            if country:
                                circuit['country'] = country

                        geo = location.get('geo', {})
                        if isinstance(geo, dict):
                            lat = geo.get('latitude')
                            lon = geo.get('longitude')
                            if lat and lat != 0:
                                circuit['lat'] = str(lat)
                            if lon and lon != 0:
                                circuit['long'] = str(lon)
            except Exception as e:
                logger.debug(f"Failed to parse ld+json for circuit: {e}")

        if not circuit['name']:
            circuit_elem = soup.find(text=re.compile(r'Circuit', re.IGNORECASE))
            if circuit_elem:
                circuit['name'] = circuit_elem.strip()

        img = soup.select_one('img[src*="Circuit"], img[src*="circuit"], img[alt*="circuit"]')
        if img:
            image_url = img.get('src', '')
            if image_url:
                if not image_url.startswith('http'):
                    image_url = self.base_url + image_url
                try:
                    circuit['image_base64'] = await self._download_image_as_base64(client, image_url)
                except Exception as e:
                    logger.warning(f"Failed to download circuit image: {e}")

        stats = soup.find_all(text=re.compile(r'\d+\s*laps', re.IGNORECASE))
        for stat in stats:
            match = re.search(r'(\d+)\s*laps', stat, re.IGNORECASE)
            if match:
                circuit['laps'] = int(match.group(1))
                break

        if not circuit['name'] and not circuit['laps']:
            raise Exception("Failed to extract circuit information")

        return circuit

    async def _download_image_as_base64(self, client: httpx.AsyncClient, url: str) -> str:
        response = await client.get(url)
        response.raise_for_status()
        return base64.b64encode(response.content).decode('utf-8')

    def _extract_weekend_dates(self, soup: BeautifulSoup, season: int) -> tuple:
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'SportsEvent':
                    start_date = data.get('startDate')
                    end_date = data.get('endDate')
                    if start_date and end_date:
                        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        return int(start_dt.timestamp()), int(end_dt.timestamp())
            except:
                pass

        date_elems = soup.find_all(text=re.compile(r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', re.IGNORECASE))

        dates = []
        for elem in date_elems[:5]:
            match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', elem, re.IGNORECASE)
            if match:
                day = int(match.group(1))
                month_str = match.group(2)
                month = datetime.strptime(month_str, '%b').month
                dt = datetime(season, month, day)
                dates.append(int(dt.timestamp()))

        if dates:
            dates.sort()
            return dates[0], dates[-1]

        return 0, 0

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
                logger.warning(f"Skipping invalid session link: {href}")
                continue

            for path_key, session_type in session_type_map.items():
                if session_type in fetched_types:
                    continue

                if href.endswith(f'/{path_key}') or f'/{path_key}' in href:
                    try:
                        if not href.startswith('http'):
                            full_url = self.base_url + href
                        else:
                            full_url = href

                        session_data = await self._fetch_session_data(client, full_url, session_type, season)

                        if session_data:
                            if session_data['date'] == 0:
                                raise Exception(f"Failed to extract date for session {session_type}")
                            sessions.append(session_data)
                            fetched_types.add(session_type)

                        await asyncio.sleep(0.5)
                        break
                    except Exception as e:
                        logger.error(f"Failed to fetch session {session_type}: {e}")
                        raise

        return sessions

    async def _fetch_session_data(self, client: httpx.AsyncClient, url: str, session_type: str, season: int) -> Dict:
        try:
            html = await self._fetch_with_retry(client, url, max_retries=2)
        except Exception as e:
            logger.warning(f"Failed to fetch session from {url}: {e}")
            raise

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

    def _extract_session_date(self, soup: BeautifulSoup, season: int) -> int:
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'SportsEvent':
                    start_date = data.get('startDate')
                    if start_date:
                        dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                        return int(dt.timestamp())
            except:
                pass

        date_elems = soup.find_all(text=re.compile(r'\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', re.IGNORECASE))
        for elem in date_elems:
            match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})', elem, re.IGNORECASE)
            if match:
                day = int(match.group(1))
                month_str = match.group(2)
                year = int(match.group(3))
                if year == season:
                    month = datetime.strptime(month_str, '%b').month
                    dt = datetime(year, month, day)
                    return int(dt.timestamp())

        return 0

    def _parse_session_results(self, soup: BeautifulSoup) -> List[Dict]:
        results = []

        table = soup.select_one('table')
        if not table:
            return []

        rows = table.select('tbody tr')
        for row in rows:
            cells = row.select('td')
            if len(cells) < 5:
                continue

            try:
                position_text = cells[0].text.strip()
                position = int(re.search(r'\d+', position_text).group()) if re.search(r'\d+', position_text) else 0

                driver_number_text = cells[1].text.strip()
                driver_number = int(re.search(r'\d+', driver_number_text).group()) if re.search(r'\d+', driver_number_text) else 0

                driver_name_raw = cells[2].text.strip()
                driver_code_match = re.search(r'[A-Z]{3}$', driver_name_raw)
                driver_code = driver_code_match.group() if driver_code_match else ''
                driver_name = re.sub(r'[A-Z]{3}$', '', driver_name_raw).strip()
                if not driver_name:
                    driver_name = driver_name_raw

                team = cells[3].text.strip()

                cell_4_text = cells[4].text.strip()
                is_race = bool(re.match(r'^\d+$', cell_4_text))

                if is_race:
                    laps = int(cell_4_text) if cell_4_text.isdigit() else 0
                    time = cells[5].text.strip() if len(cells) > 5 else ''
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
            except Exception as e:
                logger.debug(f"Failed to parse result row: {e}")
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

        raise Exception(f"Failed to fetch {url} after {max_retries} retries")
