import asyncio

from fastapi import APIRouter, Depends
from ib_insync import IB

from auth import require_auth
from dependencies import get_ib
from models import AccountSummaryItem, PnLResponse, PositionResponse

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/summary", response_model=list[AccountSummaryItem])
async def get_account_summary(ib: IB = Depends(get_ib)):
    # accountValues() returns the values TWS pushes automatically on connect.
    # reqAccountSummaryAsync() requires a separate subscription that may not
    # be active, so we prefer the already-cached values here.
    items = ib.accountValues()
    return [
        AccountSummaryItem(
            account=item.account,
            tag=item.tag,
            value=item.value,
            currency=item.currency,
        )
        for item in items
    ]


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(ib: IB = Depends(get_ib)):
    positions = ib.positions()
    return [
        PositionResponse(
            account=p.account,
            symbol=p.contract.symbol,
            sec_type=p.contract.secType,
            exchange=p.contract.exchange,
            currency=p.contract.currency,
            con_id=p.contract.conId,
            position=p.position,
            avg_cost=p.avgCost,
        )
        for p in positions
    ]


@router.get("/pnl", response_model=PnLResponse)
async def get_pnl(account: str | None = None, ib: IB = Depends(get_ib)):
    acct = account or ib.managedAccounts()[0]
    pnl = ib.reqPnL(acct)
    await asyncio.sleep(1.0)
    ib.cancelPnL(acct)
    return PnLResponse(
        account=acct,
        daily_pnl=pnl.dailyPnL,
        unrealized_pnl=pnl.unrealizedPnL,
        realized_pnl=pnl.realizedPnL,
    )
