from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

from .config import settings
from .scrapers.ergast import ErgastClient
from .grpc_client.data_scheduler_client import DataSchedulerClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="WIBM fetcher_service", version="0.1.0")

ergast = ErgastClient(settings.ERGAST_API_URL)
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

        proto_seasons = ergast.to_proto(seasons_data)
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

    except Exception as e:
        logger.error(f"Fetch error: {e}")
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
