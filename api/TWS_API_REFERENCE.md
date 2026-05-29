# TWS API Reference

This project exposes the Interactive Brokers TWS/IB Gateway API on **port 8888** via socat port-forwarding (internal ports 7496 for live, 7497 for paper trading). This reference covers how to connect and retrieve account data, positions, orders, and market data programmatically.

The TWS API is **socket-based**, not REST/HTTP. All interaction goes through a persistent TCP connection using a proprietary binary protocol.

---

## Libraries

Two Python libraries can communicate with the TWS API:

| Library | Package | Style | Best for |
|---|---|---|---|
| `ib_insync` | `pip install ib_insync` | Synchronous + async, high-level | Most use cases |
| `ibapi` | `pip install ibapi` | Callback-based (EWrapper/EClient) | Low-level control |

**This document prioritizes `ib_insync`** — it hides the callback complexity and makes common tasks one-liners. Native `ibapi` examples are included for completeness.

---

## 1. Connection

### ib_insync

```python
from ib_insync import IB

ib = IB()
ib.connect('localhost', 8888, clientId=1)

# ... do work ...

ib.disconnect()
```

**clientId**: Identifies this client session. TWS allows up to 32 simultaneous connections — use different IDs for multiple clients (e.g., 1 for your main script, 2 for a monitor, etc.). Using `clientId=0` grants master session access (can manage orders placed by other clients).

**Timeout**: Default connection timeout is 4 seconds. Increase with `timeout=10` if TWS is slow to respond.

**Context manager** (auto-disconnects):

```python
with IB().connect('localhost', 8888, clientId=1) as ib:
    positions = ib.positions()
```

### ibapi (native)

```python
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
import threading

class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=''):
        print(f"Error {errorCode}: {errorString}")

app = IBApp()
app.connect('localhost', 8888, clientId=1)

thread = threading.Thread(target=app.run, daemon=True)
thread.start()
```

The native API is event-driven: you send requests via `EClient` methods and receive data via `EWrapper` callbacks that you override.

---

## 2. Account Balances

### ib_insync

```python
from ib_insync import IB

ib = IB()
ib.connect('localhost', 8888, clientId=1)

summary = ib.accountSummary()  # list of AccountValue objects

# Print all values
for item in summary:
    print(f"{item.tag}: {item.value} {item.currency}")

# Extract specific values
def get_tag(summary, tag, currency='USD'):
    return next((v.value for v in summary if v.tag == tag and v.currency == currency), None)

net_liq     = get_tag(summary, 'NetLiquidation')
cash        = get_tag(summary, 'TotalCashValue')
buying_pwr  = get_tag(summary, 'BuyingPower')
gross_pos   = get_tag(summary, 'GrossPositionValue')
avail_funds = get_tag(summary, 'AvailableFunds')
maint_margin = get_tag(summary, 'MaintMarginReq')

ib.disconnect()
```

**Key account tags:**

| Tag | Description |
|---|---|
| `NetLiquidation` | Total account value (cash + positions) |
| `TotalCashValue` | Cash on hand |
| `BuyingPower` | Available purchasing power |
| `GrossPositionValue` | Total market value of all positions |
| `AvailableFunds` | Funds available without margin call risk |
| `MaintMarginReq` | Current maintenance margin requirement |
| `InitMarginReq` | Initial margin required to open current positions |
| `UnrealizedPnL` | Unrealized P&L across all positions |
| `RealizedPnL` | Realized P&L for the day |
| `ExcessLiquidity` | Excess liquidity (cushion above margin) |
| `Cushion` | % excess liquidity / net liquidation |
| `FullInitMarginReq` | Full initial margin if all pending orders fill |
| `LookAheadAvailFunds` | Projected available funds next margin check |

For a **single-account** setup, `accountSummary()` covers everything. For **multi-account** (advisor/family office), pass `group='All'` and inspect the `account` field on each `AccountValue`.

### ibapi (native)

```python
from ibapi.client import EClient
from ibapi.wrapper import EWrapper

TAGS = "NetLiquidation,TotalCashValue,BuyingPower,GrossPositionValue,AvailableFunds,MaintMarginReq"

class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def accountSummary(self, reqId, account, tag, value, currency):
        print(f"[{account}] {tag}: {value} {currency}")

    def accountSummaryEnd(self, reqId):
        print("Account summary complete")
        self.disconnect()

app = IBApp()
app.connect('localhost', 8888, clientId=1)
app.reqAccountSummary(reqId=1, groupName='All', tags=TAGS)
app.run()
```

For per-account updates that push whenever values change, use `reqAccountUpdates(subscribe=True, acctCode='YOUR_ACCOUNT')` with the `updateAccountValue` callback.

---

## 3. Current Positions

### ib_insync

```python
from ib_insync import IB

ib = IB()
ib.connect('localhost', 8888, clientId=1)

positions = ib.positions()  # list of Position(account, contract, position, avgCost)

for pos in positions:
    print(f"{pos.contract.symbol} {pos.contract.secType}: "
          f"{pos.position} @ avg {pos.avgCost:.2f} "
          f"(account: {pos.account})")

ib.disconnect()
```

Each `Position` has:
- `account` — account number string
- `contract` — `Contract` object (symbol, secType, exchange, currency, etc.)
- `position` — float, number of shares/contracts (negative = short)
- `avgCost` — average cost per share/contract

To get current market value, combine with a market data request (see section 8).

### ibapi (native)

```python
class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def position(self, account, contract, position, avgCost):
        print(f"{account} | {contract.symbol} {contract.secType}: "
              f"{position} @ {avgCost:.2f}")

    def positionEnd(self):
        print("All positions received")
        self.cancelPositions()
        self.disconnect()

app = IBApp()
app.connect('localhost', 8888, clientId=1)
app.reqPositions()
app.run()
```

Use `cancelPositions()` to stop receiving real-time position updates after you have the snapshot.

---

## 4. Open Orders

### ib_insync

```python
from ib_insync import IB

ib = IB()
ib.connect('localhost', 8888, clientId=1)

# Orders placed by THIS client only
orders = ib.openOrders()

# All open orders across all clients (requires clientId=0 or master session)
trades = ib.reqAllOpenOrders()

for trade in trades:
    o = trade.order
    c = trade.contract
    s = trade.orderStatus
    print(f"OrderId {o.orderId}: {o.action} {o.totalQuantity} {c.symbol} "
          f"{o.orderType} @ {o.lmtPrice or 'MKT'} — status: {s.status}")

ib.disconnect()
```

Each `Trade` object has:
- `contract` — the instrument
- `order` — `Order` object with `orderId`, `action` (BUY/SELL), `totalQuantity`, `orderType`, `lmtPrice`, `auxPrice` (stop price), `tif` (time in force)
- `orderStatus` — `OrderStatus` with `status` (PreSubmitted, Submitted, Filled, Cancelled, etc.), `filled`, `remaining`, `avgFillPrice`
- `fills` — list of `Fill` objects for partial fills

**Order status values:**

| Status | Meaning |
|---|---|
| `PreSubmitted` | Received by TWS, not yet sent to exchange |
| `Submitted` | Live at exchange |
| `Filled` | Fully filled |
| `PartiallyFilled` | Some shares filled, rest active |
| `Cancelled` | Cancelled |
| `Inactive` | Rejected or expired |

### ibapi (native)

```python
class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def openOrder(self, orderId, contract, order, orderState):
        print(f"OrderId {orderId}: {order.action} {order.totalQuantity} "
              f"{contract.symbol} {order.orderType} — {orderState.status}")

    def openOrderEnd(self):
        print("All open orders received")
        self.disconnect()

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice,
                    permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"OrderId {orderId}: {status} — filled {filled}, remaining {remaining}")

app = IBApp()
app.connect('localhost', 8888, clientId=1)
app.reqAllOpenOrders()  # all clients; use reqOpenOrders() for this client only
app.run()
```

---

## 5. P&L (Profit & Loss)

### ib_insync

```python
from ib_insync import IB

ib = IB()
ib.connect('localhost', 8888, clientId=1)

account = ib.managedAccounts()[0]  # get your account number

# Subscribe to account-level P&L (updates in real time)
pnl = ib.reqPnL(account)
ib.sleep(1)  # wait for first update
print(f"Daily P&L: {pnl.dailyPnL:.2f}")
print(f"Unrealized: {pnl.unrealizedPnL:.2f}")
print(f"Realized:   {pnl.realizedPnL:.2f}")

# Per-position P&L (need conId from a position)
positions = ib.positions()
for pos in positions:
    conId = pos.contract.conId
    pnl_single = ib.reqPnLSingle(account, '', conId)
    ib.sleep(0.5)
    print(f"{pos.contract.symbol}: unrealized {pnl_single.unrealizedPnL:.2f}, "
          f"realized {pnl_single.realizedPnL:.2f}, pos {pnl_single.pos}")

ib.disconnect()
```

`PnL` object fields: `dailyPnL`, `unrealizedPnL`, `realizedPnL`
`PnLSingle` object fields: `pos`, `dailyPnL`, `unrealizedPnL`, `realizedPnL`, `value`

### ibapi (native)

```python
class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def pnl(self, reqId, dailyPnL, unrealizedPnL, realizedPnL):
        print(f"Daily: {dailyPnL:.2f}, Unrealized: {unrealizedPnL:.2f}, Realized: {realizedPnL:.2f}")

    def pnlSingle(self, reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value):
        print(f"Position: {pos}, Daily: {dailyPnL:.2f}, Value: {value:.2f}")

app = IBApp()
app.connect('localhost', 8888, clientId=1)
app.reqPnL(reqId=1, account='U1234567', modelCode='')
# For single position: app.reqPnLSingle(reqId=2, account='U1234567', modelCode='', conid=265598)
app.run()
```

---

## 6. Executions / Trade History

### ib_insync

```python
from ib_insync import IB
from ib_insync import ExecutionFilter
import datetime

ib = IB()
ib.connect('localhost', 8888, clientId=1)

# All fills from today
fills = ib.executions()

for fill in fills:
    e = fill.execution
    c = fill.contract
    print(f"{e.time} | {e.side} {e.shares} {c.symbol} @ {e.price:.2f} "
          f"(orderId: {e.orderId}, execId: {e.execId})")

ib.disconnect()
```

Each `Fill` has:
- `contract` — the instrument traded
- `execution` — `Execution` object with `execId`, `time`, `side` (BOT/SLD), `shares`, `price`, `cumQty`, `avgPrice`, `orderId`, `permId`
- `commissionReport` — `CommissionReport` with `commission`, `currency`, `realizedPNL`

### ibapi (native)

```python
from ibapi.execution import ExecutionFilter

class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def execDetails(self, reqId, contract, execution):
        print(f"{execution.time} | {execution.side} {execution.shares} "
              f"{contract.symbol} @ {execution.price:.2f}")

    def execDetailsEnd(self, reqId):
        self.disconnect()

    def commissionReport(self, commissionReport):
        print(f"Commission: {commissionReport.commission} {commissionReport.currency}, "
              f"Realized PnL: {commissionReport.realizedPNL}")

app = IBApp()
app.connect('localhost', 8888, clientId=1)

filt = ExecutionFilter()
# filt.side = 'BOT'           # filter by side
# filt.symbol = 'AAPL'        # filter by symbol
# filt.time = '20240101 00:00:00'  # only executions after this time

app.reqExecutions(reqId=1, execFilter=filt)
app.run()
```

---

## 7. Contract Specification

Before requesting market data or placing orders you need a `Contract` object. Always call `qualifyContracts()` to resolve ambiguities (multiple exchanges, expiries, etc.).

### ib_insync

```python
from ib_insync import IB, Stock, Option, Future, Forex, Contract

ib = IB()
ib.connect('localhost', 8888, clientId=1)

# US Stock
aapl = Stock('AAPL', 'SMART', 'USD')

# ETF
spy = Stock('SPY', 'SMART', 'USD')

# Forex
eurusd = Forex('EURUSD')  # expands to EUR.USD on IDEALPRO

# E-mini S&P 500 futures (front month)
es = Future('ES', exchange='CME', currency='USD')

# Option (must specify expiry, strike, right)
aapl_call = Option('AAPL', '20241220', 200, 'C', 'SMART')

# Resolve and fill in missing fields (conId, exchange, etc.)
ib.qualifyContracts(aapl, spy, eurusd, es, aapl_call)

print(aapl.conId)   # confirmed contract ID
ib.disconnect()
```

**Generic Contract builder:**
```python
c = Contract()
c.symbol   = 'AAPL'
c.secType  = 'STK'       # STK, OPT, FUT, CASH (forex), IND, CFD, BOND
c.exchange = 'SMART'     # SMART for stocks; CME, NYMEX, etc. for futures
c.currency = 'USD'
```

---

## 8. Market Data (Live Quotes)

### ib_insync — snapshot (one-time price fetch)

```python
from ib_insync import IB, Stock

ib = IB()
ib.connect('localhost', 8888, clientId=1)

contract = Stock('AAPL', 'SMART', 'USD')
ib.qualifyContracts(contract)

# Snapshot: returns once, no ongoing subscription
ticker = ib.reqMktData(contract, snapshot=True)
ib.sleep(2)  # wait for data to arrive

print(f"Bid: {ticker.bid}  Ask: {ticker.ask}  Last: {ticker.last}  Close: {ticker.close}")

ib.cancelMktData(contract)
ib.disconnect()
```

### ib_insync — streaming (live updates)

```python
from ib_insync import IB, Stock

ib = IB()
ib.connect('localhost', 8888, clientId=1)

contract = Stock('AAPL', 'SMART', 'USD')
ib.qualifyContracts(contract)

ticker = ib.reqMktData(contract)

def on_tick(tickers):
    for t in tickers:
        print(f"{t.contract.symbol}: bid={t.bid} ask={t.ask} last={t.last} volume={t.volume}")

ib.pendingTickersEvent += on_tick
ib.run()  # blocks; press Ctrl+C to stop
```

**Key `Ticker` fields:** `bid`, `bidSize`, `ask`, `askSize`, `last`, `lastSize`, `volume`, `open`, `high`, `low`, `close`, `halted`, `vwap`

### ibapi (native)

```python
class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def tickPrice(self, reqId, tickType, price, attrib):
        # tickType: 1=bid, 2=ask, 4=last, 6=high, 7=low, 9=close
        tick_names = {1: 'Bid', 2: 'Ask', 4: 'Last', 6: 'High', 7: 'Low', 9: 'Close'}
        print(f"{tick_names.get(tickType, tickType)}: {price}")

    def tickSize(self, reqId, tickType, size):
        # tickType: 0=bid size, 3=ask size, 5=last size, 8=volume
        pass

contract = Contract()
contract.symbol = 'AAPL'
contract.secType = 'STK'
contract.exchange = 'SMART'
contract.currency = 'USD'

app = IBApp()
app.connect('localhost', 8888, clientId=1)
app.reqMktData(reqId=1, contract=contract,
               genericTickList='',
               snapshot=True,         # True = one-time; False = streaming
               regulatorySnapshot=False,
               mktDataOptions=[])
app.run()
```

**Note:** Market data requires active IB market data subscriptions. Without a subscription, you get delayed data (15–20 min). IB provides free delayed data for most US equities.

---

## 9. Historical Data

### ib_insync

```python
from ib_insync import IB, Stock
import datetime

ib = IB()
ib.connect('localhost', 8888, clientId=1)

contract = Stock('AAPL', 'SMART', 'USD')
ib.qualifyContracts(contract)

bars = ib.reqHistoricalData(
    contract,
    endDateTime='',             # '' = now; or datetime object / '20240101 00:00:00'
    durationStr='30 D',         # how far back: '1 D', '1 W', '1 M', '1 Y', '30 D'
    barSizeSetting='1 hour',    # bar size (see table below)
    whatToShow='TRADES',        # TRADES, MIDPOINT, BID, ASK, BID_ASK, ADJUSTED_LAST
    useRTH=True,                # True = regular trading hours only
    formatDate=1,               # 1 = string date, 2 = unix timestamp
    keepUpToDate=False,         # True = streaming updates
)

for bar in bars:
    print(f"{bar.date}  O:{bar.open:.2f}  H:{bar.high:.2f}  "
          f"L:{bar.low:.2f}  C:{bar.close:.2f}  V:{bar.volume}")

ib.disconnect()
```

**Bar sizes:** `1 secs`, `5 secs`, `15 secs`, `30 secs`, `1 min`, `2 mins`, `3 mins`, `5 mins`, `10 mins`, `15 mins`, `20 mins`, `30 mins`, `1 hour`, `2 hours`, `3 hours`, `4 hours`, `8 hours`, `1 day`, `1 week`, `1 month`

**Duration strings:** `S` (seconds), `D` (days), `W` (weeks), `M` (months), `Y` (years) — e.g., `'30 D'`, `'1 Y'`

**Historical data pacing:** IB rate-limits historical data requests. Max ~60 requests per 10 minutes per account. Use `ib.sleep(1)` between consecutive requests.

### ibapi (native)

```python
class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def historicalData(self, reqId, bar):
        print(f"{bar.date}  O:{bar.open}  H:{bar.high}  L:{bar.low}  C:{bar.close}  V:{bar.volume}")

    def historicalDataEnd(self, reqId, start, end):
        print(f"Historical data complete: {start} to {end}")
        self.disconnect()

app = IBApp()
app.connect('localhost', 8888, clientId=1)
app.reqHistoricalData(
    reqId=1,
    contract=contract,
    endDateTime='',
    durationStr='30 D',
    barSizeSetting='1 hour',
    whatToShow='TRADES',
    useRTH=1,
    formatDate=1,
    keepUpToDate=False,
    chartOptions=[]
)
app.run()
```

---

## 10. Placing & Cancelling Orders

**Note:** This project's `ibc/config.ini` has `ReadOnlyApi=no`, so order placement is enabled.

### ib_insync

```python
from ib_insync import IB, Stock, MarketOrder, LimitOrder, StopOrder

ib = IB()
ib.connect('localhost', 8888, clientId=1)

contract = Stock('AAPL', 'SMART', 'USD')
ib.qualifyContracts(contract)

# Market order
trade = ib.placeOrder(contract, MarketOrder('BUY', 10))

# Limit order
trade = ib.placeOrder(contract, LimitOrder('BUY', 10, lmtPrice=180.00))

# Stop order
trade = ib.placeOrder(contract, StopOrder('SELL', 10, stopPrice=175.00))

# Wait for acknowledgement
ib.sleep(1)
print(f"OrderId: {trade.order.orderId}, Status: {trade.orderStatus.status}")

# Modify: change quantity and re-place with same orderId
trade.order.totalQuantity = 5
ib.placeOrder(contract, trade.order)

# Cancel
ib.cancelOrder(trade.order)

ib.disconnect()
```

**Order types available:**

| Class | Description |
|---|---|
| `MarketOrder(action, qty)` | Execute at market price |
| `LimitOrder(action, qty, lmtPrice)` | Execute at limit price or better |
| `StopOrder(action, qty, stopPrice)` | Market order triggered at stop price |
| `StopLimitOrder(action, qty, lmtPrice, stopPrice)` | Limit order triggered at stop price |
| `Order()` | Generic — set all fields manually |

**Common `Order` fields:**
- `tif` — time in force: `'DAY'`, `'GTC'` (good till cancelled), `'IOC'` (immediate or cancel), `'GTD'`
- `outsideRth` — `True` to allow pre/after-market execution
- `account` — account number (required for advisor accounts)
- `transmit` — `True` (default) to send immediately; `False` to hold in TWS

### ibapi (native)

```python
from ibapi.order import Order

class IBApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.nextOrderId = None

    def nextValidId(self, orderId):
        self.nextOrderId = orderId
        self.place_order()

    def place_order(self):
        contract = Contract()
        contract.symbol = 'AAPL'
        contract.secType = 'STK'
        contract.exchange = 'SMART'
        contract.currency = 'USD'

        order = Order()
        order.action = 'BUY'
        order.totalQuantity = 10
        order.orderType = 'LMT'
        order.lmtPrice = 180.00
        order.tif = 'DAY'

        self.placeOrder(self.nextOrderId, contract, order)

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice,
                    permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"Order {orderId}: {status}")

app = IBApp()
app.connect('localhost', 8888, clientId=1)
app.run()
```

The `nextValidId` callback fires immediately on connect with a valid order ID. Always use this ID (or higher) for new orders.

---

## 11. Real-Time Subscriptions (Event-Driven)

`ib_insync` exposes events you can subscribe to for real-time monitoring without polling:

```python
from ib_insync import IB, Stock

ib = IB()
ib.connect('localhost', 8888, clientId=1)

# Called whenever an order's status changes
def on_order_status(trade):
    print(f"Order {trade.order.orderId}: {trade.orderStatus.status}")

ib.orderStatusEvent += on_order_status

# Called whenever a position changes
def on_position(position):
    print(f"Position update: {position.contract.symbol} = {position.position}")

ib.positionEvent += on_position

# Called on each new fill/execution
def on_exec(trade, fill):
    print(f"Fill: {fill.execution.shares} {trade.contract.symbol} @ {fill.execution.price}")

ib.execDetailsEvent += on_exec

# Called when account value changes (requires reqAccountUpdates subscription)
def on_account_value(value):
    if value.tag == 'NetLiquidation':
        print(f"Net Liq: {value.value} {value.currency}")

ib.accountValueEvent += on_account_value

# Start the event loop (blocks until disconnected or Ctrl+C)
ib.run()
```

**Available events:** `orderStatusEvent`, `positionEvent`, `execDetailsEvent`, `commissionReportEvent`, `accountValueEvent`, `pendingTickersEvent`, `tickNewsEvent`, `errorEvent`, `connectedEvent`, `disconnectedEvent`

---

## 12. Managed Accounts

For advisor or family office accounts:

```python
from ib_insync import IB

ib = IB()
ib.connect('localhost', 8888, clientId=1)

accounts = ib.managedAccounts()
print(accounts)  # e.g., ['U1234567', 'U7654321']

# Get positions per account
for acc in accounts:
    positions = [p for p in ib.positions() if p.account == acc]
    print(f"\n{acc}:")
    for p in positions:
        print(f"  {p.contract.symbol}: {p.position}")

ib.disconnect()
```

---

## 13. Connection Details for This Project

| Parameter | Value | Notes |
|---|---|---|
| Host | `localhost` | Or the Docker host IP if connecting from outside |
| Port | `8888` | Live trading (socat → internal 7496) |
| Paper port | `8888` | Same port, but set `IBC_TradingMode=paper` in `.env` |
| clientId | 1–32 | Any unique integer per simultaneous client |
| Master clientId | 0 | Can view/cancel orders from all other clients |

**Switching to paper trading:** Edit `.env` and set `IBC_TradingMode=paper`, then `docker compose up -d --force-recreate tws` to restart the container with paper mode.

**API security:** Port 8888 has no authentication. Bind it to localhost only (already the case in `docker-compose.yml` — the port is not published to `0.0.0.0` by default; verify with `docker compose port tws 8888`).

---

## 14. Quick Reference: Common Patterns

```python
from ib_insync import IB, Stock, Forex, Future

ib = IB()
ib.connect('localhost', 8888, clientId=1)

# --- Snapshot of everything ---
account      = ib.managedAccounts()[0]
summary      = ib.accountSummary()
positions    = ib.positions()
open_orders  = ib.reqAllOpenOrders()
executions   = ib.executions()
pnl          = ib.reqPnL(account); ib.sleep(1)

def val(tag):
    return next((v.value for v in summary if v.tag == tag and v.currency == 'USD'), 'N/A')

print(f"Account:        {account}")
print(f"Net Liq:        {val('NetLiquidation')}")
print(f"Cash:           {val('TotalCashValue')}")
print(f"Buying Power:   {val('BuyingPower')}")
print(f"Unrealized P&L: {pnl.unrealizedPnL:.2f}")
print(f"Daily P&L:      {pnl.dailyPnL:.2f}")
print(f"\nPositions ({len(positions)}):")
for p in positions:
    print(f"  {p.contract.symbol}: {p.position:+.0f} @ {p.avgCost:.2f}")
print(f"\nOpen Orders ({len(open_orders)}):")
for t in open_orders:
    print(f"  {t.order.action} {t.order.totalQuantity} {t.contract.symbol} "
          f"{t.order.orderType} — {t.orderStatus.status}")

ib.disconnect()
```

---

## 15. Error Codes

Common TWS error codes you'll encounter:

| Code | Meaning |
|---|---|
| 200 | No security definition found for this request |
| 201 | Order rejected |
| 202 | Order cancelled |
| 321 | Server error when reading an account (check account number) |
| 354 | Requested market data not subscribed |
| 502 | Couldn't connect to TWS (not running or wrong port) |
| 504 | Not connected |
| 1100 | Connectivity between IB and TWS lost |
| 1101 | Connectivity restored, data lost (resubscribe) |
| 1102 | Connectivity restored, data maintained |
| 2104 | Market data farm connected |
| 2106 | HMDS data farm connected |
| 2158 | Sec-def data farm connected |

Codes 2100–2199 are informational (not errors). Codes 1100–1102 indicate network events requiring resubscription to market data.
