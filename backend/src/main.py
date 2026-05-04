import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.models import PropertyUrlRequest
from src.reporters.pipeline import start_run, run_pipeline, get_run

app = FastAPI(title="Real Estate Investment Advisor")
_executor = ThreadPoolExecutor(max_workers=3)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analysis", status_code=202)
async def create_analysis(req: PropertyUrlRequest) -> dict:
    run_id = start_run(req.url)
    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, run_pipeline, run_id, req.url)
    return {"run_id": run_id, "status": "running"}


@app.get("/api/analysis/{run_id}")
async def get_analysis(run_id: str) -> dict:
    result = get_run(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
