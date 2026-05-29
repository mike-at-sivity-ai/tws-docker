from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Contract ──────────────────────────────────────────────────────────────────

class ContractSpec(BaseModel):
    symbol: Optional[str] = Field(None, examples=["AAPL"])
    sec_type: Literal["STK", "OPT", "FUT", "CASH", "IND", "CFD", "BOND"] = "STK"
    exchange: str = "SMART"
    currency: str = "USD"
    expiry: Optional[str] = Field(None, description="YYYYMM or YYYYMMDD for futures/options")
    strike: Optional[float] = Field(None, description="Option strike price")
    right: Optional[Literal["C", "P"]] = Field(None, description="Option right: C=call, P=put")
    multiplier: Optional[str] = None
    con_id: Optional[int] = Field(None, description="IB contract ID; overrides all other fields if set")


# ── Order placement ───────────────────────────────────────────────────────────

class PlaceOrderRequest(BaseModel):
    contract: ContractSpec
    action: Literal["BUY", "SELL"]
    quantity: float = Field(..., gt=0)
    order_type: Literal["MKT", "LMT", "STP", "STP LMT"] = "MKT"
    limit_price: Optional[float] = Field(None, description="Required for LMT and STP LMT")
    stop_price: Optional[float] = Field(None, description="Required for STP and STP LMT")
    tif: Literal["DAY", "GTC", "IOC", "GTD"] = "DAY"
    outside_rth: bool = False
    account: Optional[str] = Field(None, description="Account number; defaults to primary managed account")


# ── Response models ───────────────────────────────────────────────────────────

class AccountSummaryItem(BaseModel):
    account: str
    tag: str
    value: str
    currency: str


class PositionResponse(BaseModel):
    account: str
    symbol: str
    sec_type: str
    exchange: str
    currency: str
    con_id: int
    position: float
    avg_cost: float


class PnLResponse(BaseModel):
    account: str
    daily_pnl: Optional[float]
    unrealized_pnl: Optional[float]
    realized_pnl: Optional[float]


class OrderResponse(BaseModel):
    order_id: int
    perm_id: int
    account: str
    action: str
    total_quantity: float
    order_type: str
    lmt_price: Optional[float]
    aux_price: Optional[float]
    tif: str
    status: str
    filled: float
    remaining: float
    avg_fill_price: float
    symbol: str
    sec_type: str


class PlaceOrderResponse(BaseModel):
    order_id: int
    perm_id: int
    status: str


class ExecutionResponse(BaseModel):
    exec_id: str
    order_id: int
    perm_id: int
    symbol: str
    sec_type: str
    time: str
    side: str
    shares: float
    price: float
    cum_qty: float
    avg_price: float
    commission: Optional[float]
    realized_pnl: Optional[float]
    currency: str


class QuoteResponse(BaseModel):
    symbol: str
    sec_type: str
    bid: Optional[float]
    bid_size: Optional[float]
    ask: Optional[float]
    ask_size: Optional[float]
    last: Optional[float]
    last_size: Optional[float]
    volume: Optional[float]
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    halted: Optional[float]


class HistoricalBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    average: Optional[float]
    bar_count: Optional[int]


class ContractResponse(BaseModel):
    con_id: int
    symbol: str
    sec_type: str
    exchange: str
    primary_exchange: str
    currency: str
    local_symbol: str
    trading_class: str
    description: Optional[str]
