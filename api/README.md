# TWS REST API

FastAPI service that wraps the Interactive Brokers TWS API. Runs as a Docker container alongside TWS and is accessible through nginx at `/api/`.

## Base URL

```
http://<host>:6080/api
```

Replace `<host>` with your server IP or hostname (e.g. `192.168.1.15`). All examples below use `localhost:6080`.

## Authentication

Every endpoint (except `/health`) requires one of:

| Method | How |
|--------|-----|
| API key | `X-API-Key: <key>` request header |
| Authelia session | Browser session cookie from logging in at `/authelia/` |

The API key is in `.env` as `API_KEY`. Set the variable for convenience:

```bash
export API_KEY=<your-key-from-.env>
```

All curl examples below use `$API_KEY`.

---

## Endpoints

### Health

#### `GET /health`

No authentication required. Returns whether the TWS socket connection is active.

```bash
curl http://localhost:6080/api/health
```

```json
{"connected": true}
```

While TWS is starting up (can take ~90s after container start), `connected` is `false` and all other endpoints return HTTP 503.

---

### Account

#### `GET /account/summary`

All account values pushed by TWS on connect: balances, margin, buying power, P&L tags, and more.

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:6080/api/account/summary
```

```json
[
  {"account": "U12345678", "tag": "NetLiquidation",  "value": "125432.50", "currency": "USD"},
  {"account": "U12345678", "tag": "TotalCashValue",  "value": "45210.00",  "currency": "USD"},
  {"account": "U12345678", "tag": "BuyingPower",     "value": "180640.00", "currency": "USD"},
  {"account": "U12345678", "tag": "MaintMarginReq",  "value": "12450.00",  "currency": "USD"},
  ...
]
```

Filter for specific tags in the response:

```bash
curl -s -H "X-API-Key: $API_KEY" http://localhost:6080/api/account/summary \
  | python3 -c "import sys,json; [print(v['tag'], v['value']) for v in json.load(sys.stdin) if v['tag'] in ('NetLiquidation','TotalCashValue','BuyingPower')]"
```

---

#### `GET /account/positions`

All current open positions across all managed accounts.

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:6080/api/account/positions
```

```json
[
  {
    "account":   "U12345678",
    "symbol":    "AAPL",
    "sec_type":  "STK",
    "exchange":  "NASDAQ",
    "currency":  "USD",
    "con_id":    265598,
    "position":  100.0,
    "avg_cost":  175.42
  }
]
```

---

#### `GET /account/pnl`

Daily, unrealized, and realized P&L for an account. Defaults to the first managed account.

| Query param | Type | Default | Description |
|-------------|------|---------|-------------|
| `account`   | str  | first managed account | IB account number |

```bash
# Primary account
curl -H "X-API-Key: $API_KEY" http://localhost:6080/api/account/pnl

# Specific account
curl -H "X-API-Key: $API_KEY" "http://localhost:6080/api/account/pnl?account=U12345678"
```

```json
{
  "account":        "U12345678",
  "daily_pnl":      1523.40,
  "unrealized_pnl": 8741.20,
  "realized_pnl":   312.00
}
```

---

### Market Data

Quotes use snapshot mode (no persistent subscription). Without a live IB market data subscription, values are delayed 15–20 minutes.

#### `GET /market-data/quote`

Real-time or delayed snapshot quote.

| Query param | Type   | Default  | Description |
|-------------|--------|----------|-------------|
| `symbol`    | str    | —        | Ticker symbol (required unless `con_id` given) |
| `sec_type`  | str    | `STK`    | `STK`, `OPT`, `FUT`, `CASH`, `IND` |
| `exchange`  | str    | `SMART`  | Exchange or `SMART` for IB routing |
| `currency`  | str    | `USD`    | ISO currency code |
| `con_id`    | int    | —        | IB contract ID; overrides all other fields |

```bash
# Stock by symbol
curl -H "X-API-Key: $API_KEY" "http://localhost:6080/api/market-data/quote?symbol=AAPL"

# EUR/USD forex pair
curl -H "X-API-Key: $API_KEY" "http://localhost:6080/api/market-data/quote?symbol=EUR&sec_type=CASH&currency=GBP"

# By contract ID (fastest, no qualification step)
curl -H "X-API-Key: $API_KEY" "http://localhost:6080/api/market-data/quote?con_id=265598"
```

```json
{
  "symbol":    "AAPL",
  "sec_type":  "STK",
  "bid":       195.40,
  "bid_size":  200.0,
  "ask":       195.42,
  "ask_size":  300.0,
  "last":      195.41,
  "last_size": 100.0,
  "volume":    null,
  "open":      194.80,
  "high":      196.10,
  "low":       194.20,
  "close":     194.95,
  "halted":    0.0
}
```

Fields that TWS hasn't sent yet appear as `null`.

---

#### `GET /market-data/historical`

OHLCV bars for a contract.

| Query param     | Type   | Default   | Description |
|-----------------|--------|-----------|-------------|
| `symbol`        | str    | —         | Ticker (required unless `con_id` given) |
| `sec_type`      | str    | `STK`     | Security type |
| `exchange`      | str    | `SMART`   | Exchange |
| `currency`      | str    | `USD`     | Currency |
| `con_id`        | int    | —         | IB contract ID |
| `duration`      | str    | `30 D`    | How far back: `1 D`, `1 W`, `1 M`, `1 Y`, etc. |
| `bar_size`      | str    | `1 hour`  | Bar width: `1 min`, `5 mins`, `15 mins`, `1 hour`, `1 day`, etc. |
| `what_to_show`  | str    | `TRADES`  | `TRADES`, `MIDPOINT`, `BID`, `ASK`, `BID_ASK` |
| `use_rth`       | bool   | `true`    | Regular trading hours only |
| `end_date_time` | str    | `""` (now)| End time in `YYYYMMDD HH:MM:SS` format |

```bash
# Last 5 days of 1-hour AAPL bars
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:6080/api/market-data/historical?symbol=AAPL&duration=5+D&bar_size=1+hour"

# Daily bars for last month
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:6080/api/market-data/historical?symbol=AAPL&duration=1+M&bar_size=1+day"

# 1-minute bars for today only (including pre/post market)
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:6080/api/market-data/historical?symbol=AAPL&duration=1+D&bar_size=1+min&use_rth=false"

# EUR/USD midpoint bars
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:6080/api/market-data/historical?symbol=EUR&sec_type=CASH&currency=GBP&duration=1+W&bar_size=1+hour&what_to_show=MIDPOINT"
```

```json
[
  {
    "date":      "2024-01-15 09:30:00-05:00",
    "open":      185.10,
    "high":      186.40,
    "low":       184.90,
    "close":     186.20,
    "volume":    3241850.0,
    "average":   185.82,
    "bar_count": 28441
  },
  ...
]
```

> **Rate limit:** ~60 historical data requests per 10 minutes per account. The API returns HTTP 500 with a TWS error message if the limit is hit.

---

### Contracts

#### `GET /contracts`

Resolve and qualify a contract specification. Use this to find the canonical `con_id` for a symbol before making repeated market data or order requests.

| Query param | Type   | Default  | Description |
|-------------|--------|----------|-------------|
| `symbol`    | str    | —        | Ticker (required unless `con_id` given) |
| `sec_type`  | str    | `STK`    | `STK`, `OPT`, `FUT`, `CASH`, `IND`, `CFD`, `BOND` |
| `exchange`  | str    | `SMART`  | Exchange |
| `currency`  | str    | `USD`    | Currency |
| `expiry`    | str    | —        | `YYYYMM` or `YYYYMMDD` — for futures/options |
| `strike`    | float  | —        | Option strike price |
| `right`     | str    | —        | `C` (call) or `P` (put) — for options |
| `con_id`    | int    | —        | Resolve by IB contract ID directly |

```bash
# Qualify a stock
curl -H "X-API-Key: $API_KEY" "http://localhost:6080/api/contracts?symbol=AAPL"

# Futures contract (front month)
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:6080/api/contracts?symbol=ES&sec_type=FUT&exchange=CME&currency=USD"

# Option contract
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:6080/api/contracts?symbol=AAPL&sec_type=OPT&expiry=202501&strike=200&right=C"

# EUR/USD forex
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:6080/api/contracts?symbol=EUR&sec_type=CASH&currency=GBP"

# Lookup by con_id
curl -H "X-API-Key: $API_KEY" "http://localhost:6080/api/contracts?con_id=265598"
```

```json
[
  {
    "con_id":         265598,
    "symbol":         "AAPL",
    "sec_type":       "STK",
    "exchange":       "SMART",
    "primary_exchange": "",
    "currency":       "USD",
    "local_symbol":   "AAPL",
    "trading_class":  "NMS",
    "description":    ""
  }
]
```

---

### Orders

#### `GET /orders`

All open orders across all accounts (including orders placed manually in TWS).

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:6080/api/orders
```

```json
[
  {
    "order_id":       12345,
    "perm_id":        987654321,
    "account":        "U12345678",
    "action":         "BUY",
    "total_quantity": 10.0,
    "order_type":     "LMT",
    "lmt_price":      180.00,
    "aux_price":      null,
    "tif":            "DAY",
    "status":         "Submitted",
    "filled":         0.0,
    "remaining":      10.0,
    "avg_fill_price": 0.0,
    "symbol":         "AAPL",
    "sec_type":       "STK"
  }
]
```

---

#### `POST /orders`

Place a new order. Returns the order ID and initial status immediately; poll `GET /orders` to track progress.

**Request body:**

```json
{
  "contract": {
    "symbol":   "AAPL",
    "sec_type": "STK",
    "exchange": "SMART",
    "currency": "USD"
  },
  "action":       "BUY",
  "quantity":     10,
  "order_type":   "LMT",
  "limit_price":  180.00,
  "tif":          "DAY",
  "outside_rth":  false
}
```

| Field         | Type    | Required | Values |
|---------------|---------|----------|--------|
| `contract`    | object  | Yes      | See contract fields below |
| `action`      | str     | Yes      | `BUY`, `SELL` |
| `quantity`    | float   | Yes      | Number of shares/contracts |
| `order_type`  | str     | No       | `MKT` (default), `LMT`, `STP`, `STP LMT` |
| `limit_price` | float   | LMT, STP LMT | Limit price |
| `stop_price`  | float   | STP, STP LMT | Stop trigger price |
| `tif`         | str     | No       | `DAY` (default), `GTC`, `IOC`, `GTD` |
| `outside_rth` | bool    | No       | `false` (default) — allow pre/after-market |
| `account`     | str     | No       | Account number; defaults to primary managed account |

**Contract fields** (`contract` object):

| Field       | Default  | Notes |
|-------------|----------|-------|
| `symbol`    | —        | Required unless `con_id` given |
| `sec_type`  | `STK`    | |
| `exchange`  | `SMART`  | |
| `currency`  | `USD`    | |
| `expiry`    | —        | Futures/options: `YYYYMM` |
| `strike`    | —        | Options only |
| `right`     | —        | `C` or `P` (options) |
| `con_id`    | —        | Overrides all other fields |

```bash
# Market order
curl -X POST http://localhost:6080/api/orders \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contract":{"symbol":"AAPL"},"action":"BUY","quantity":1,"order_type":"MKT"}'

# Limit order
curl -X POST http://localhost:6080/api/orders \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contract":{"symbol":"AAPL"},"action":"BUY","quantity":10,"order_type":"LMT","limit_price":180.00}'

# GTC limit order, pre/after-market allowed
curl -X POST http://localhost:6080/api/orders \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contract":{"symbol":"AAPL"},"action":"SELL","quantity":5,"order_type":"LMT","limit_price":210.00,"tif":"GTC","outside_rth":true}'

# Stop-limit order
curl -X POST http://localhost:6080/api/orders \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contract":{"symbol":"AAPL"},"action":"SELL","quantity":10,"order_type":"STP LMT","stop_price":170.00,"limit_price":169.50}'

# Futures order (by con_id for precision)
curl -X POST http://localhost:6080/api/orders \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contract":{"con_id":495512551},"action":"BUY","quantity":1,"order_type":"MKT"}'
```

```json
{"order_id": 12345, "perm_id": 987654321, "status": "PreSubmitted"}
```

> **Note:** The response reflects the status ~500ms after submission. `PreSubmitted` means TWS has acknowledged it; `Submitted` means it's live at the exchange. A rejected order returns `Inactive` — check `GET /orders` for the full status message.

---

#### `DELETE /orders/{order_id}`

Cancel an open order by its `order_id` (from `GET /orders` or the `POST /orders` response).

```bash
curl -X DELETE http://localhost:6080/api/orders/12345 \
  -H "X-API-Key: $API_KEY"
```

```json
{"cancelled": true, "order_id": 12345}
```

Returns HTTP 404 if the order ID is not found in the current open orders list.

---

#### `GET /orders/executions`

Today's fills (executions) from the current TWS session. Resets when TWS restarts.

| Query param | Type | Default | Description |
|-------------|------|---------|-------------|
| `symbol`    | str  | —       | Filter fills by symbol (case-insensitive) |

```bash
# All fills today
curl -H "X-API-Key: $API_KEY" http://localhost:6080/api/orders/executions

# Fills for AAPL only
curl -H "X-API-Key: $API_KEY" "http://localhost:6080/api/orders/executions?symbol=AAPL"
```

```json
[
  {
    "exec_id":      "0001f4e8.65b3c2d1.01.01",
    "order_id":     12345,
    "perm_id":      987654321,
    "symbol":       "AAPL",
    "sec_type":     "STK",
    "time":         "2024-01-15 10:23:41",
    "side":         "BOT",
    "shares":       10.0,
    "price":        185.42,
    "cum_qty":      10.0,
    "avg_price":    185.42,
    "commission":   1.00,
    "realized_pnl": null,
    "currency":     "USD"
  }
]
```

---

## Error Responses

| HTTP | Meaning |
|------|---------|
| 401  | Missing or invalid authentication (no API key and no valid Authelia session) |
| 404  | Contract not found, or order ID not in open orders |
| 422  | Validation error — missing required field (e.g. `limit_price` for a limit order) |
| 503  | TWS is not connected — service starting up or TWS restarted |
| 500  | TWS returned an error (e.g. historical data pacing violation, order rejected) |

---

## Interactive Docs

FastAPI's Swagger UI is available at:

```
http://localhost:6080/api/docs
```

Authenticate using the **Authorize** button (enter your API key). All endpoints are testable directly from the browser.

The OpenAPI schema is at `/api/openapi.json`.

---

## Order Lifecycle Example

```bash
# 1. Place a limit buy far below market (safe for testing)
ORDER=$(curl -s -X POST http://localhost:6080/api/orders \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contract":{"symbol":"AAPL"},"action":"BUY","quantity":1,"order_type":"LMT","limit_price":1.00}')
echo $ORDER
ORDER_ID=$(echo $ORDER | python3 -c "import sys,json; print(json.load(sys.stdin)['order_id'])")

# 2. Confirm it appears in open orders
curl -s -H "X-API-Key: $API_KEY" http://localhost:6080/api/orders | python3 -m json.tool

# 3. Cancel it
curl -X DELETE http://localhost:6080/api/orders/$ORDER_ID \
  -H "X-API-Key: $API_KEY"
```

---

## Notes

- **TWS startup time:** IB Gateway takes ~90 seconds to log in after the container starts. The API returns HTTP 503 during this window.
- **Daily restart:** TWS restarts overnight (~11:45 PM ET by default). The API reconnects automatically within ~60 seconds.
- **Historical data rate limit:** ~60 requests per 10 minutes per IB account. Spread out bulk requests.
- **Market data subscriptions:** Without a live IB market data subscription, quotes are delayed 15–20 minutes.
- **clientId:** The API connects to TWS with `clientId=10`. This is separate from the TWS GUI session (clientId=0). Orders placed via the API appear in the TWS GUI and vice versa (via `GET /orders` which fetches all clients' orders).
- **Paper trading:** Switch the IBC config (`TradingMode=paper` in `ibc/config.ini`) to use a paper account. The API URL and key remain the same.
