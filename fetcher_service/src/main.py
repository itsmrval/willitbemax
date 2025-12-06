from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging
import asyncio
from datetime import datetime

from .config import settings
from .scrapers.ergast import ErgastClient
from .scrapers.f1_website import F1WebsiteClient
from .grpc_client.data_scheduler_client import DataSchedulerClient
from protobuf.gen.python import content_pb2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="WIBM fetcher_service", version="0.1.0")

ergast = ErgastClient(settings.ERGAST_API_URL)
scheduler = DataSchedulerClient(settings.DATA_SCHEDULER_URI)
f1_website = F1WebsiteClient(scheduler_client=scheduler)

@app.get("/")
async def root():
    return {"service": "fetcher_service", "status": "running"}

@app.post("/fetch/seasons")
async def fetch_seasons():
    try:
        logger.info("Fetching seasons from ergast")

        seasons_data = await ergast.fetch_seasons()
        logger.info(f"Fetched {len(seasons_data)} seasons")

        details_map = {}
        failed_seasons = []

        for season_item in seasons_data:
            year = int(season_item["season"])
            try:
                logger.info(f"Fetching details for season {year}")
                details = await ergast.fetch_season_details(year)
                details_map[year] = details
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Failed to fetch details for season {year}: {e}")
                failed_seasons.append(year)

        if failed_seasons:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch details for seasons: {failed_seasons}"
            )

        logger.info(f"Fetched details for {len(details_map)} seasons")

        proto_seasons = ergast.to_proto(seasons_data, details_map)
        response = scheduler.write_seasons(proto_seasons)

        if response.success:
            logger.info(f"Synced {response.records_affected} seasons")
            return {
                "success": True,
                "source": "ergast",
                "count": len(seasons_data),
                "timestamp": int(datetime.now().timestamp())
            }
        else:
            raise HTTPException(status_code=500, detail=response.message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fetch/rounds")
async def fetch_rounds(season: int, round: int = None, live: str = None):
    try:
        if live and round is None:
            raise HTTPException(status_code=400, detail="live parameter requires round parameter")

        if round is not None:
            logger.info(f"Fetching round {round} for season {season}" + (f" with forced live session: {live}" if live else ""))
        else:
            logger.info(f"Fetching all rounds for season {season}")

        rounds_data = await f1_website.fetch_rounds_for_season(season, specific_round_id=round, force_live_session=live)

        if not rounds_data:
            if round is not None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Round {round} not found or failed to fetch for season {season}"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to fetch all rounds (all-or-nothing strategy)"
                )

        proto_rounds = []
        for round_data in rounds_data:
            circuit_proto = content_pb2.Circuit(
                name=round_data['circuit']['name'],
                laps=round_data['circuit']['laps'],
                image_base64=round_data['circuit']['image_base64']
            )

            sessions_proto = []
            logger.info(f"Round {round_data['round_id']} has {len(round_data['sessions'])} sessions: {[s['type'] for s in round_data['sessions']]}")
            for session_data in round_data['sessions']:
                results_proto = []
                for result_data in session_data['results']:
                    results_proto.append(content_pb2.SessionResult(
                        position=result_data['position'],
                        driver_number=result_data['driver_number'],
                        driver_name=result_data['driver_name'],
                        driver_code=result_data['driver_code'],
                        team=result_data['team'],
                        time=result_data['time'],
                        laps=result_data['laps']
                    ))

                sessions_proto.append(content_pb2.Session(
                    type=session_data['type'],
                    date=session_data['date'],
                    total_laps=session_data['total_laps'],
                    current_lap=session_data['current_lap'],
                    results=results_proto,
                    is_live=session_data.get('is_live', False),
                    status=session_data.get('status', 'finished')
                ))

            proto_rounds.append(content_pb2.Round(
                round_id=round_data['round_id'],
                name=round_data['name'],
                season=round_data['season'],
                circuit=circuit_proto,
                first_date=round_data['first_date'],
                end_date=round_data['end_date'],
                sessions=sessions_proto
            ))

        rounds_proto_data = content_pb2.RoundsData(rounds=proto_rounds)
        response = scheduler.write_rounds(rounds_proto_data)

        if response.success:
            logger.info(f"Synced {response.records_affected} rounds")
            return {
                "success": True,
                "source": "f1_website",
                "count": len(rounds_data),
                "timestamp": int(datetime.now().timestamp())
            }
        else:
            raise HTTPException(status_code=500, detail=response.message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fetch rounds error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status():
    try:
        ergast_ok = await ergast.health()
        scheduler_ok = scheduler.health()

        return {
            "status": "ready",
            "ergast": ergast_ok,
            "scheduler": scheduler_ok,
            "timestamp": int(datetime.now().timestamp())
        }
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "message": str(e)})

@app.on_event("shutdown")
async def shutdown():
    scheduler.close()
