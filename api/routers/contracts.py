from fastapi import APIRouter, Depends, HTTPException
from ib_insync import Contract, IB

from auth import require_auth
from dependencies import get_ib
from models import ContractResponse

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("", response_model=list[ContractResponse])
async def qualify_contract(
    symbol: str | None = None,
    sec_type: str = "STK",
    exchange: str = "SMART",
    currency: str = "USD",
    expiry: str | None = None,
    strike: float | None = None,
    right: str | None = None,
    con_id: int | None = None,
    ib: IB = Depends(get_ib),
):
    if con_id:
        c = Contract(conId=con_id)
    elif symbol:
        c = Contract(
            symbol=symbol,
            secType=sec_type,
            exchange=exchange,
            currency=currency,
            lastTradeDateOrContractMonth=expiry or "",
            strike=strike or 0.0,
            right=right or "",
        )
    else:
        raise HTTPException(status_code=422, detail="Either 'symbol' or 'con_id' is required")

    try:
        qualified = await ib.qualifyContractsAsync(c)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not qualified:
        raise HTTPException(status_code=404, detail="No contracts found matching specification")

    return [
        ContractResponse(
            con_id=q.conId,
            symbol=q.symbol,
            sec_type=q.secType,
            exchange=q.exchange,
            primary_exchange=getattr(q, "primaryExch", ""),
            currency=q.currency,
            local_symbol=q.localSymbol,
            trading_class=q.tradingClass,
            description=getattr(q, "description", None),
        )
        for q in qualified
    ]
