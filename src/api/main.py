import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nifty 100 Financial Intelligence API",
    description="REST API for the Nifty 100 Financial Intelligence Platform.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next,
):
    start = time.perf_counter()

    response = await call_next(request)

    elapsed = time.perf_counter() - start

    logger.info(
        "%s %s -> %s (%.3fs)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )

    return response


API_PREFIX = "/api/v1"

app.include_router(
    companies.router,
    prefix=API_PREFIX,
    tags=["Companies"],
)

app.include_router(
    screener.router,
    prefix=API_PREFIX,
    tags=["Screener"],
)

app.include_router(
    sectors.router,
    prefix=API_PREFIX,
    tags=["Sectors"],
)

app.include_router(
    peers.router,
    prefix=API_PREFIX,
    tags=["Peers"],
)

app.include_router(
    valuation.router,
    prefix=API_PREFIX,
    tags=["Valuation"],
)

app.include_router(
    portfolio.router,
    prefix=API_PREFIX,
    tags=["Portfolio"],
)

app.include_router(
    documents.router,
    prefix=API_PREFIX,
    tags=["Documents"],
)

app.include_router(
    health.router,
    prefix=API_PREFIX,
    tags=["Health"],
)


@app.get("/")
def root():
    """Basic API root endpoint."""
    return {
        "name": "Nifty 100 Financial Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
