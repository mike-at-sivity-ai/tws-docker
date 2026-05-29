import asyncio

from fastapi import APIRouter, Depends, HTTPException
from ib_insync import (
    Contract,
    IB,
    LimitOrder,
    MarketOrder,
    StopLimitOrder,
    StopOrder,
)

from auth import require_auth
from dependencies import get_ib
from models import (
    ContractSpec,
    ExecutionResponse,
    OrderResponse,
    PlaceOrderRequest,
    PlaceOrderResponse,
)

router = APIRouter(dependencies=[Depends(require_auth)])


def _build_contract_from_spec(spec: ContractSpec) -> Contract:
    if spec.con_id:
        return Contract(conId=spec.con_id)
    if not spec.symbol:
        raise HTTPException(status_code=422, detail="Either 'symbol' or 'con_id' is required in contract")
    c = Contract(
        symbol=spec.symbol,
        secType=spec.sec_type,
        exchange=spec.exchange,
        currency=spec.currency,
    )
    if spec.expiry:
        c.lastTradeDateOrContractMonth = spec.expiry
    if spec.strike:
        c.strike = spec.strike
    if spec.right:
        c.right = spec.right
    if spec.multiplier:
        c.multiplier = spec.multiplier
    return c


def _trade_to_response(trade) -> OrderResponse:
    return OrderResponse(
        order_id=trade.order.orderId,
        perm_id=trade.order.permId,
        account=trade.order.account,
        action=trade.order.action,
        total_quantity=trade.order.totalQuantity,
        order_type=trade.order.orderType,
        lmt_price=trade.order.lmtPrice if trade.order.lmtPrice != 0 else None,
        aux_price=trade.order.auxPrice if trade.order.auxPrice != 0 else None,
        tif=trade.order.tif,
        status=trade.orderStatus.status,
        filled=trade.orderStatus.filled,
        remaining=trade.orderStatus.remaining,
        avg_fill_price=trade.orderStatus.avgFillPrice,
        symbol=trade.contract.symbol,
        sec_type=trade.contract.secType,
    )


@router.get("", response_model=list[OrderResponse])
async def get_open_orders(ib: IB = Depends(get_ib)):
    trades = await ib.reqAllOpenOrdersAsync()
    return [_trade_to_response(t) for t in trades]


@router.post("", response_model=PlaceOrderResponse, status_code=201)
async def place_order(req: PlaceOrderRequest, ib: IB = Depends(get_ib)):
    c = _build_contract_from_spec(req.contract)
    qualified = await ib.qualifyContractsAsync(c)
    if not qualified:
        raise HTTPException(status_code=404, detail="Contract not found")

    match req.order_type:
        case "MKT":
            order = MarketOrder(req.action, req.quantity)
        case "LMT":
            if req.limit_price is None:
                raise HTTPException(status_code=422, detail="limit_price required for LMT orders")
            order = LimitOrder(req.action, req.quantity, req.limit_price)
        case "STP":
            if req.stop_price is None:
                raise HTTPException(status_code=422, detail="stop_price required for STP orders")
            order = StopOrder(req.action, req.quantity, req.stop_price)
        case "STP LMT":
            if req.limit_price is None or req.stop_price is None:
                raise HTTPException(status_code=422, detail="Both limit_price and stop_price required for STP LMT")
            order = StopLimitOrder(req.action, req.quantity, req.limit_price, req.stop_price)
        case _:
            raise HTTPException(status_code=422, detail=f"Unknown order_type: {req.order_type}")

    order.tif = req.tif
    order.outsideRth = req.outside_rth
    if req.account:
        order.account = req.account

    trade = ib.placeOrder(qualified[0], order)
    await asyncio.sleep(0.5)

    return PlaceOrderResponse(
        order_id=trade.order.orderId,
        perm_id=trade.order.permId,
        status=trade.orderStatus.status,
    )


@router.delete("/{order_id}")
async def cancel_order(order_id: int, ib: IB = Depends(get_ib)):
    trades = await ib.reqAllOpenOrdersAsync()
    target = next((t for t in trades if t.order.orderId == order_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found in open orders")
    ib.cancelOrder(target.order)
    await asyncio.sleep(0.5)
    return {"cancelled": True, "order_id": order_id}


@router.get("/executions", response_model=list[ExecutionResponse])
async def get_executions(symbol: str | None = None, ib: IB = Depends(get_ib)):
    fills = ib.fills()
    result = []
    for fill in fills:
        if symbol and fill.contract.symbol.upper() != symbol.upper():
            continue
        result.append(
            ExecutionResponse(
                exec_id=fill.execution.execId,
                order_id=fill.execution.orderId,
                perm_id=fill.execution.permId,
                symbol=fill.contract.symbol,
                sec_type=fill.contract.secType,
                time=str(fill.execution.time),
                side=fill.execution.side,
                shares=fill.execution.shares,
                price=fill.execution.price,
                cum_qty=fill.execution.cumQty,
                avg_price=fill.execution.avgPrice,
                commission=getattr(fill.commissionReport, "commission", None),
                realized_pnl=getattr(fill.commissionReport, "realizedPNL", None),
                currency=getattr(fill.commissionReport, "currency", fill.contract.currency),
            )
        )
    return result
