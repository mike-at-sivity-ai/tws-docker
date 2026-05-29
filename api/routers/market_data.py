import asyncio

from fastapi import APIRouter, Depends, HTTPException
from ib_insync import Contract, IB

from auth import require_auth
from dependencies import get_ib
from models import HistoricalBar, QuoteResponse

router = APIRouter(dependencies=[Depends(require_auth)])


def _build_contract(
    symbol: str | None,
    sec_type: str,
    exchange: str,
    currency: str,
    con_id: int | None,
) -> Contract:
    if con_id:
        return Contract(conId=con_id)
    if not symbol:
        raise HTTPException(status_code=422, detail="Either 'symbol' or 'con_id' is required")
    return Contract(symbol=symbol, secType=sec_type, exchange=exchange, currency=currency)


@router.get("/quote", response_model=QuoteResponse)
async def get_quote(
    symbol: str | None = None,
    sec_type: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
    con_id: int | None = None,
    ib: IB = Depends(get_ib),
):
    contract = _build_contract(symbol, sec_type, exchange, currency, con_id)
    qualified = await ib.qualifyContractsAsync(contract)
    if not qualified:
        raise HTTPException(status_code=404, detail="Contract not found")
    contract = qualified[0]

    ticker = ib.reqMktData(contract, snapshot=True)
    await asyncio.sleep(2.0)
    ib.cancelMktData(contract)

    return QuoteResponse(
        symbol=contract.symbol,
        sec_type=contract.secType,
        bid=ticker.bid,
        bid_size=ticker.bidSize,
        ask=ticker.ask,
        ask_size=ticker.askSize,
        last=ticker.last,
        last_size=ticker.lastSize,
        volume=ticker.volume,
        open=ticker.open,
        high=ticker.high,
        low=ticker.low,
        close=ticker.close,
        halted=ticker.halted,
    )


@router.get("/historical", response_model=list[HistoricalBar])
async def get_historical(
    symbol: str | None = None,
    sec_type: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
    con_id: int | None = None,
    duration: str = "30 D",
    bar_size: str = "1 hour",
    what_to_show: str = "TRADES",
    use_rth: bool = True,
    end_date_time: str = "",
    ib: IB = Depends(get_ib),
):
    contract = _build_contract(symbol, sec_type, exchange, currency, con_id)
    qualified = await ib.qualifyContractsAsync(contract)
    if not qualified:
        raise HTTPException(status_code=404, detail="Contract not found")

    try:
        bars = await ib.reqHistoricalDataAsync(
            contract=qualified[0],
            endDateTime=end_date_time,
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth,
            formatDate=1,
            keepUpToDate=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TWS error: {exc}")

    return [
        HistoricalBar(
            date=str(b.date),
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume,
            average=getattr(b, "average", None),
            bar_count=getattr(b, "barCount", None),
        )
        for b in bars
    ]
