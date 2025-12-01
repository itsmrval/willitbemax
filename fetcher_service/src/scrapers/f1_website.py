import httpx
import logging
import asyncio
import base64
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class F1WebsiteClient:
    def __init__(self):
        self.base_url = "https://www.formula1.com"
        self.timeout = 30.0
        self.max_retries = 3

    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching {url} (attempt {attempt + 1}/{self.max_retries})")
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"Rate limited on {url}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"HTTP error fetching {url}: {e}")
                    raise
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"Error fetching {url}, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to fetch {url} after {self.max_retries} attempts: {e}")
                    raise

    async def fetch_rounds_for_season(self, year: int) -> List[Dict]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/en/racing/{year}"
            response = await self._fetch_with_retry(client, url)
            soup = BeautifulSoup(response.text, 'lxml')
            
            rounds = []
            seen_urls = set()
            
            all_links = soup.find_all('a', href=lambda x: x and f'/en/racing/{year}/' in str(x) and x != f'/en/racing/{year}')
            
            for link in all_links:
                href = link.get('href', '')
                if not href or href in seen_urls:
                    continue
                
                seen_urls.add(href)
                
                if not href.startswith('http'):
                    full_url = f"{self.base_url}{href}"
                else:
                    full_url = href
                
                context_data = link.get('data-f1rd-a7s-context', '')
                round_name = None
                
                if context_data:
                    try:
                        import base64
                        import json
                        decoded = base64.b64decode(context_data)
                        context = json.loads(decoded)
                        if 'raceName' in context:
                            round_name = context['raceName']
                    except:
                        pass
                
                if not round_name:
                    parent = link.parent
                    for _ in range(3):
                        if parent:
                            text_elem = parent.find('p', class_=lambda x: x and 'display-xl-bold' in str(x) if x else False)
                            if text_elem:
                                round_name = text_elem.get_text(strip=True)
                                break
                            text_elem = parent.find('span', class_=lambda x: x and 'body-xs-semibold' in str(x) if x else False)
                            if text_elem:
                                full_text = text_elem.get_text(strip=True)
                                if 'FORMULA 1' in full_text and 'GRAND PRIX' in full_text:
                                    round_name = full_text
                                    break
                            parent = parent.parent if hasattr(parent, 'parent') else None
                
                if not round_name:
                    url_parts = href.rstrip('/').split('/')
                    if url_parts:
                        slug = url_parts[-1]
                        round_name = slug.replace('-', ' ').title()
                
                if round_name and full_url:
                    rounds.append({
                        'round_id': len(rounds),
                        'name': round_name,
                        'url': full_url,
                        'season': year
                    })
            
            if not rounds:
                raise ValueError(f"No rounds found for season {year}")
            
            return rounds

    async def fetch_round_details(self, round_url: str, round_id: int, season: int) -> Dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await self._fetch_with_retry(client, round_url)
            soup = BeautifulSoup(response.text, 'lxml')
            
            circuit_name = "Unknown Circuit"
            circuit_laps = 0
            circuit_image_base64 = ""
            locality = ""
            country = ""
            lat = ""
            long = ""
            
            circuit_elem = soup.find('div', class_='circuit-info') or \
                          soup.find('h2', string=lambda x: x and 'Circuit' in x)
            if circuit_elem:
                circuit_name = circuit_elem.get_text(strip=True)
            
            circuit_img = soup.find('img', class_='circuit-map') or \
                         soup.find('img', alt=lambda x: x and 'circuit' in x.lower() if x else False)
            if circuit_img:
                img_url = circuit_img.get('src', '')
                if img_url and not img_url.startswith('http'):
                    img_url = f"{self.base_url}{img_url}"
                if img_url:
                    try:
                        img_response = await self._fetch_with_retry(client, img_url)
                        circuit_image_base64 = base64.b64encode(img_response.content).decode('utf-8')
                    except Exception as e:
                        logger.warning(f"Could not fetch circuit image: {e}")
            
            laps_elem = soup.find(string=lambda x: x and 'lap' in x.lower() if x else False)
            if laps_elem:
                try:
                    laps_text = laps_elem.strip()
                    circuit_laps = int(''.join(filter(str.isdigit, laps_text)))
                except:
                    circuit_laps = 50
            
            sessions = []
            
            import json
            script_tags = soup.find_all('script', type='application/json')
            for script in script_tags:
                try:
                    json_data = json.loads(script.string)
                    if isinstance(json_data, dict) and 'props' in json_data:
                        page_props = json_data.get('props', {}).get('pageProps', {})
                        if 'raceSchedule' in page_props:
                            schedule = page_props['raceSchedule']
                            if isinstance(schedule, list):
                                for sched_item in schedule:
                                    if isinstance(sched_item, dict) and 'sessionType' in sched_item and 'date' in sched_item:
                                        session_type = self._normalize_session_type(sched_item.get('sessionType', ''))
                                        try:
                                            date_str = sched_item.get('date', '')
                                            if date_str:
                                                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                                timestamp = int(dt.timestamp())
                                                if 0 <= timestamp <= 2147483647:
                                                    sessions.append({
                                                        'type': session_type,
                                                        'date': timestamp,
                                                        'total_laps': circuit_laps if session_type == 'race' else 0,
                                                        'current_laps': 1
                                                    })
                                        except (ValueError, OverflowError, OSError):
                                            pass
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
            
            if not sessions:
                session_elements = soup.find_all('div', class_='session') or \
                                 soup.find_all('li', class_='schedule-item')
            
                for session_elem in session_elements:
                    try:
                        session_type = None
                        session_date = None
                        
                        type_elem = session_elem.find('span', class_='session-type') or \
                                   session_elem.find('h3') or \
                                   session_elem.find('p', class_='session-name')
                        if type_elem:
                            session_type_text = type_elem.get_text(strip=True).lower()
                            session_type = self._normalize_session_type(session_type_text)
                        
                        date_elem = session_elem.find('time') or \
                                   session_elem.find('span', class_='date')
                        if date_elem:
                            datetime_attr = date_elem.get('datetime')
                            if datetime_attr:
                                try:
                                    datetime_str = datetime_attr.replace('Z', '+00:00')
                                    if len(datetime_str) < 10:
                                        continue
                                    dt = datetime.fromisoformat(datetime_str)
                                    timestamp = int(dt.timestamp())
                                    if timestamp < 0 or timestamp > 2147483647:
                                        continue
                                    session_date = timestamp
                                except (ValueError, OverflowError, OSError):
                                    pass
                        
                        if session_type and session_date:
                            sessions.append({
                                'type': session_type,
                                'date': session_date,
                                'total_laps': circuit_laps if session_type == 'race' else 0,
                                'current_laps': 1
                            })
                    
                    except Exception as e:
                        logger.error(f"Error parsing session: {e}")
                        continue
            
            return {
                'circuit': {
                    'name': circuit_name,
                    'lat': lat,
                    'long': long,
                    'locality': locality,
                    'country': country,
                    'image_base64': circuit_image_base64,
                    'laps': circuit_laps
                },
                'sessions': sessions
            }

    def _normalize_session_type(self, session_text: str) -> str:
        session_text = session_text.lower().strip()
        
        if 'practice 1' in session_text or 'fp1' in session_text:
            return 'practice_1'
        elif 'practice 2' in session_text or 'fp2' in session_text:
            return 'practice_2'
        elif 'practice 3' in session_text or 'fp3' in session_text:
            return 'practice_3'
        elif 'sprint qualifying' in session_text or 'sprint shootout' in session_text:
            return 'sprint_qualifying'
        elif 'sprint' in session_text:
            return 'sprint'
        elif 'qualifying' in session_text or 'quali' in session_text:
            return 'qualifying'
        elif 'race' in session_text:
            return 'race'
        else:
            return 'unknown'

    async def fetch_session_results(self, season: int, round_name: str, session_type: str) -> List[Dict]:
        session_url_map = {
            'practice_1': 'practice-1',
            'practice_2': 'practice-2',
            'practice_3': 'practice-3',
            'qualifying': 'qualifying',
            'sprint_qualifying': 'sprint-qualifying',
            'sprint': 'sprint',
            'race': 'race'
        }
        
        session_url_part = session_url_map.get(session_type, session_type.replace('_', '-'))
        
        round_slug = round_name.lower().replace(' ', '-').replace('formula-1-', '')
        
        possible_urls = [
            f"{self.base_url}/en/results/{season}/races/{round_slug}/{session_url_part}",
            f"{self.base_url}/en/results.html/{season}/races/{round_slug}/{session_url_part}.html"
        ]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = None
            for url in possible_urls:
                try:
                    response = await self._fetch_with_retry(client, url)
                    break
                except:
                    continue
            
            if not response:
                logger.warning(f"Could not fetch results for {round_name} {session_type}")
                return []
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            results = []
            table = soup.find('table', class_='resultsarchive-table') or \
                   soup.find('table')
            
            if not table:
                logger.warning(f"No results table found for {round_name} {session_type}")
                return []
            
            rows = table.find_all('tr')[1:]
            
            for row in rows:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 5:
                        continue
                    
                    position = int(cells[0].get_text(strip=True))
                    driver_number_text = cells[1].get_text(strip=True)
                    driver_number = int(driver_number_text) if driver_number_text.isdigit() else 0
                    
                    driver_name = cells[2].get_text(strip=True)
                    
                    team = cells[3].get_text(strip=True)
                    
                    time_text = cells[4].get_text(strip=True)
                    
                    laps = 0
                    if len(cells) > 5:
                        laps_text = cells[5].get_text(strip=True)
                        if laps_text.isdigit():
                            laps = int(laps_text)
                    
                    results.append({
                        'position': position,
                        'driver_number': driver_number,
                        'driver_name': driver_name,
                        'team': team,
                        'time': time_text,
                        'laps': laps
                    })
                
                except Exception as e:
                    logger.error(f"Error parsing result row: {e}")
                    continue
            
            return results

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/en")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

