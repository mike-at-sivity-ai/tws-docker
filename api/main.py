import asyncio
import json
import logging
import math
from contextlib import asynccontextmanager

import ib_insync
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import TWS_CLIENT_ID, TWS_HOST, TWS_PORT, TWS_TIMEOUT
from dependencies import ib_state
from routers import account, contracts, market_data, orders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Must be called before the event loop starts so ib_insync's internal
# synchronous calls can co-exist with uvicorn's asyncio loop.
ib_insync.util.patchAsyncio()


def _sanitize(obj):
    """Recursively replace float nan/inf with None so json.dumps produces valid JSON."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


class NanSafeJSONResponse(JSONResponse):
    """Render float('nan')/inf as JSON null instead of the invalid token NaN."""

    def render(self, content) -> bytes:
        return json.dumps(_sanitize(content)).encode()


async def _reconnect_loop() -> None:
    while True:
        if not ib_state.ib.isConnected():
            for attempt in range(1, 6):
                try:
                    await ib_state.ib.connectAsync(
                        host=TWS_HOST,
                        port=TWS_PORT,
                        clientId=TWS_CLIENT_ID,
                        timeout=TWS_TIMEOUT,
                    )
                    logger.info("Connected to TWS on attempt %d", attempt)
                    break
                except Exception as exc:
                    logger.warning("Connect attempt %d failed: %s", attempt, exc)
                    await asyncio.sleep(30)
            else:
                # All attempts failed; pause before the outer loop retries
                await asyncio.sleep(60)
        else:
            # Connected — wait for a disconnect before looping
            done = asyncio.Event()
            ib_state.ib.disconnectedEvent += lambda: done.set()
            await done.wait()
            logger.warning("TWS disconnected. Waiting 60s before reconnect attempt...")
            await asyncio.sleep(60)


def _on_tws_error(req_id: int, error_code: int, error_string: str, contract) -> None:
    # Informational codes — not real errors
    if error_code in (2100, 2103, 2104, 2105, 2106, 2107, 2108, 2158):
        logger.debug("TWS info [%d]: %s", error_code, error_string)
        return
    if error_code in (1100, 1101, 1102):
        logger.warning("TWS connectivity event [%d]: %s", error_code, error_string)
        return
    logger.error("TWS error reqId=%d code=%d: %s", req_id, error_code, error_string)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ib_state.ib.errorEvent += _on_tws_error
    logger.info(
        "Connecting to TWS at %s:%d (clientId=%d)", TWS_HOST, TWS_PORT, TWS_CLIENT_ID
    )
    try:
        await ib_state.ib.connectAsync(
            host=TWS_HOST,
            port=TWS_PORT,
            clientId=TWS_CLIENT_ID,
            timeout=TWS_TIMEOUT,
            readonly=False,
        )
        logger.info(
            "Connected to TWS. Managed accounts: %s", ib_state.ib.managedAccounts()
        )
    except Exception as exc:
        logger.error(
            "Initial TWS connection failed (will retry on reconnect loop): %s", exc
        )

    reconnect_task = asyncio.create_task(_reconnect_loop())

    yield

    reconnect_task.cancel()
    if ib_state.ib.isConnected():
        ib_state.ib.disconnect()
        logger.info("Disconnected from TWS")


app = FastAPI(
    title="TWS API",
    description="REST wrapper for Interactive Brokers TWS via ib_insync",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=NanSafeJSONResponse,
)

app.include_router(account.router, prefix="/account", tags=["Account"])
app.include_router(market_data.router, prefix="/market-data", tags=["Market Data"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(contracts.router, prefix="/contracts", tags=["Contracts"])


@app.get("/health", tags=["Health"])
async def health():
    return {"connected": ib_state.ib.isConnected()}
