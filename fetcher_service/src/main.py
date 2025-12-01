from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging
import asyncio
from datetime import datetime

from .config import settings
from .scrapers.ergast import ErgastClient
from .scrapers.f1_website import F1WebsiteClient
from .grpc_client.data_scheduler_client import DataSchedulerClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="WIBM fetcher_service", version="0.1.0")

ergast = ErgastClient(settings.ERGAST_API_URL)
f1_website = F1WebsiteClient()
scheduler = DataSchedulerClient(settings.DATA_SCHEDULER_URI)

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
async def fetch_rounds(season: int, round: int = None):
    try:
        logger.info(f"Fetching rounds for season {season}" + (f" round {round}" if round is not None else ""))
        
        all_rounds = await f1_website.fetch_rounds_for_season(season)
        
        if round is not None:
            all_rounds = [r for r in all_rounds if r['round_id'] == round]
            if not all_rounds:
                raise HTTPException(status_code=404, detail=f"Round {round} not found for season {season}")
        
        logger.info(f"Found {len(all_rounds)} rounds to process")
        
        rounds_data = []
        failed_rounds = []
        
        for round_info in all_rounds:
            try:
                logger.info(f"Fetching details for {round_info['name']}")
                
                round_details = await f1_website.fetch_round_details(
                    round_info['url'],
                    round_info['round_id'],
                    season
                )
                await asyncio.sleep(1)
                
                sessions_with_results = []
                for session in round_details['sessions']:
                    try:
                        logger.info(f"Fetching results for {session['type']}")
                        results = await f1_website.fetch_session_results(
                            season,
                            round_info['name'],
                            session['type']
                        )
                        session['results'] = results
                        sessions_with_results.append(session)
                        await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Failed to fetch results for {session['type']}: {e}")
                        session['results'] = []
                        sessions_with_results.append(session)
                
                # Compile complete round data
                rounds_data.append({
                    'round_id': round_info['round_id'],
                    'name': round_info['name'],
                    'season': season,
                    'circuit': round_details['circuit'],
                    'sessions': sessions_with_results,
                    'first_date': sessions_with_results[0]['date'] if sessions_with_results else 0,
                    'end_date': sessions_with_results[-1]['date'] if sessions_with_results else 0
                })
                
            except Exception as e:
                logger.error(f"Failed to fetch data for {round_info['name']}: {e}")
                failed_rounds.append(round_info['name'])
        
        if failed_rounds:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch data for rounds: {failed_rounds}. No data was written."
            )
        
        logger.info(f"Successfully fetched all data for {len(rounds_data)} rounds")
        
        proto_rounds = rounds_to_proto(rounds_data)
        
        response = scheduler.write_rounds(proto_rounds)
        
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


def rounds_to_proto(rounds_data: list):
    from protobuf.gen.python import content_pb2
    
    rounds = content_pb2.RoundsData()
    
    for round_data in rounds_data:
        round_msg = rounds.rounds.add()
        round_msg.round_id = round_data['round_id']
        round_msg.name = round_data['name']
        round_msg.season = round_data['season']
        first_date = round_data.get('first_date', 0)
        if first_date is None or not isinstance(first_date, int) or first_date < 0 or first_date > 2147483647:
            first_date = 0
        round_msg.first_date = first_date
        end_date = round_data.get('end_date', 0)
        if end_date is None or not isinstance(end_date, int) or end_date < 0 or end_date > 2147483647:
            end_date = 0
        round_msg.end_date = end_date
        
        circuit = round_data['circuit']
        round_msg.circuit.name = circuit['name']
        round_msg.circuit.lat = circuit['lat']
        round_msg.circuit.long = circuit['long']
        round_msg.circuit.locality = circuit['locality']
        round_msg.circuit.country = circuit['country']
        round_msg.circuit.image_base64 = circuit['image_base64']
        round_msg.circuit.laps = circuit['laps']
        
        for session_data in round_data['sessions']:
            session = round_msg.sessions.add()
            session.type = session_data['type']
            date_val = session_data.get('date', 0)
            if date_val is None or not isinstance(date_val, int) or date_val < 0 or date_val > 2147483647:
                date_val = 0
            session.date = date_val
            session.total_laps = session_data['total_laps']
            session.current_laps = session_data['current_laps']
            
            for result_data in session_data['results']:
                result = session.results.add()
                result.position = result_data['position']
                result.driver_number = result_data['driver_number']
                result.driver_name = result_data['driver_name']
                result.team = result_data['team']
                result.time = result_data['time']
                result.laps = result_data['laps']
    
    return rounds


@app.get("/status")
async def status():
    try:
        ergast_ok = await ergast.health()
        f1_website_ok = await f1_website.health()
        scheduler_ok = scheduler.health()

        return {
            "status": "ready",
            "ergast": ergast_ok,
            "f1_website": f1_website_ok,
            "scheduler": scheduler_ok,
            "timestamp": int(datetime.now().timestamp())
        }
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "message": str(e)})

@app.on_event("shutdown")
async def shutdown():
    scheduler.close()
