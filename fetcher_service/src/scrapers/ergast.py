import httpx
import logging
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class ErgastClient:
    def __init__(self, url: str):
        self.url = url
        self.timeout = 10.0

    async def fetch_seasons(self) -> List[Dict]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.url}/seasons.json?limit=100")
            response.raise_for_status()
            return response.json()["MRData"]["SeasonTable"]["Seasons"]

    def to_proto(self, seasons_data: List[Dict]):
        from protobuf.gen.python import content_pb2

        seasons = content_pb2.SeasonsData()
        for item in seasons_data:
            season = seasons.seasons.add()
            year = int(item["season"])
            season.year = year
            season.rounds = 0
            season.status = self._status(year)
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

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.url}/current.json")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
