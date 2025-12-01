import httpx
import logging
import asyncio
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class ErgastClient:
    def __init__(self, url: str):
        self.url = url
        self.timeout = 10.0

    async def fetch_seasons(self, start_year: int = 2010) -> List[Dict]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.url}/seasons.json?limit=100")
            response.raise_for_status()
            seasons = response.json()["MRData"]["SeasonTable"]["Seasons"]
            return [s for s in seasons if int(s["season"]) >= start_year]

    async def _fetch_with_retry(self, client: httpx.AsyncClient, url: str, max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    logger.warning(f"Rate limited on {url}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def fetch_season_details(self, year: int, max_retries: int = 3) -> Dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            driver_response = await self._fetch_with_retry(client, f"{self.url}/{year}/driverStandings.json", max_retries)
            driver_data = driver_response.json()["MRData"]["StandingsTable"]["StandingsLists"]
            await asyncio.sleep(0.5)

            constructor_response = await self._fetch_with_retry(client, f"{self.url}/{year}/constructorStandings.json", max_retries)
            constructor_data = constructor_response.json()["MRData"]["StandingsTable"]["StandingsLists"]
            await asyncio.sleep(0.5)

            races_response = await self._fetch_with_retry(client, f"{self.url}/{year}.json", max_retries)
            races_data = races_response.json()["MRData"]["RaceTable"]["Races"]
            await asyncio.sleep(0.5)

            details = {
                "driver_standings": [],
                "constructor_standings": [],
                "total_drivers": 0,
                "total_teams": 0,
                "rounds": len(races_data),
                "current_round": 0,
                "start_date": None,
                "end_date": None
            }

            if driver_data and len(driver_data) > 0:
                standings = driver_data[0].get("DriverStandings", [])
                details["total_drivers"] = len(standings)
                for standing in standings:
                    driver = standing.get("Driver", {})
                    constructors = standing.get("Constructors", [])
                    details["driver_standings"].append({
                        "position": int(standing.get("position", 0)),
                        "driver_name": f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip(),
                        "driver_code": driver.get("code", ""),
                        "driver_number": int(driver.get("permanentNumber", 0)) if driver.get("permanentNumber") else 0,
                        "team": constructors[0].get("name", "") if constructors else "",
                        "points": int(float(standing.get("points", 0))),
                        "wins": int(standing.get("wins", 0))
                    })

            if constructor_data and len(constructor_data) > 0:
                standings = constructor_data[0].get("ConstructorStandings", [])
                details["total_teams"] = len(standings)
                for standing in standings:
                    constructor = standing.get("Constructor", {})
                    details["constructor_standings"].append({
                        "position": int(standing.get("position", 0)),
                        "team": constructor.get("name", ""),
                        "points": int(float(standing.get("points", 0))),
                        "wins": int(standing.get("wins", 0))
                    })

            if races_data:
                details["start_date"] = races_data[0]["date"]
                details["end_date"] = races_data[-1]["date"]

                now = datetime.now().date()
                for idx, race in enumerate(races_data):
                    race_date = datetime.strptime(race["date"], "%Y-%m-%d").date()
                    if race_date > now:
                        details["current_round"] = idx
                        break
                else:
                    details["current_round"] = len(races_data)

            return details

    def to_proto(self, seasons_data: List[Dict], details_map: Dict[int, Dict] = None):
        from protobuf.gen.python import content_pb2

        seasons = content_pb2.SeasonsData()
        for item in seasons_data:
            season = seasons.seasons.add()
            year = int(item["season"])
            season.year = year
            season.status = self._status(year)

            if details_map and year in details_map:
                details = details_map[year]
                season.rounds = details.get("rounds", 0)
                season.current_round = details.get("current_round", 0)
                season.total_drivers = details.get("total_drivers", 0)
                season.total_teams = details.get("total_teams", 0)

                for ds in details.get("driver_standings", []):
                    standing = season.driver_standings.add()
                    standing.position = ds["position"]
                    standing.driver_name = ds["driver_name"]
                    standing.driver_code = ds["driver_code"]
                    standing.driver_number = ds["driver_number"]
                    standing.team = ds["team"]
                    standing.points = ds["points"]
                    standing.wins = ds["wins"]

                for cs in details.get("constructor_standings", []):
                    standing = season.constructor_standings.add()
                    standing.position = cs["position"]
                    standing.team = cs["team"]
                    standing.points = cs["points"]
                    standing.wins = cs["wins"]

                if details.get("start_date"):
                    start_dt = datetime.strptime(details["start_date"], "%Y-%m-%d")
                    season.start_date = int(start_dt.timestamp())
                else:
                    season.start_date = int(datetime(year, 1, 1).timestamp())

                if details.get("end_date"):
                    end_dt = datetime.strptime(details["end_date"], "%Y-%m-%d")
                    season.end_date = int(end_dt.timestamp())
                else:
                    season.end_date = int(datetime(year, 12, 31).timestamp())
            else:
                season.rounds = 0
                season.current_round = 0
                season.total_drivers = 0
                season.total_teams = 0
                season.start_date = int(datetime(year, 1, 1).timestamp())
                season.end_date = int(datetime(year, 12, 31).timestamp())

        return seasons

    def _status(self, year: int) -> str:
        now = datetime.now().year
        if year < now:
            return "completed"
        elif year == now:
            return "in_progress"
        return "upcoming"

    async def fetch_circuit_for_round(self, season: int, round_num: int) -> Dict:
        """Fetch circuit information (including lat/long) for a specific round from Ergast"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await self._fetch_with_retry(client, f"{self.url}/{season}/{round_num}.json")
                races = response.json()["MRData"]["RaceTable"]["Races"]

                if not races or len(races) == 0:
                    logger.warning(f"No circuit data found in Ergast for season {season} round {round_num}")
                    return {}

                race = races[0]
                circuit = race.get("Circuit", {})
                location = circuit.get("Location", {})

                return {
                    "lat": location.get("lat", "0"),
                    "long": location.get("long", "0"),
                    "locality": location.get("locality", ""),
                    "country": location.get("country", "")
                }
            except Exception as e:
                logger.error(f"Failed to fetch circuit from Ergast for {season}/{round_num}: {e}")
                return {}

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.url}/current.json")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
