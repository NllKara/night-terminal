# NIGHT Quant Terminal

Personal quant market intelligence terminal with live charting, real OHLCV adapters, volume analysis, probability/EV outputs and deterministic Quant Chat.

## What is live now
- TradingView interactive chart
- BTCUSD OHLCV + real exchange volume from Binance public REST (no key)
- XAU/FX OHLCV + tick-volume through OANDA practice v20 when a free practice token is provided
- Twelve Data Basic adapter for free real-time FX/crypto REST where the symbol is available on the plan
- Quant Chat grounded in the current calculated analysis

## Quant engine
The terminal does not generate random scores. It calculates from observed bars:
- log returns
- multi-horizon return z-score
- OLS log-price trend slope significance (t-stat) and R²
- Kaufman Efficiency Ratio
- realized volatility
- ATR and ATR z-score
- volume z-score
- signed-volume pressure proxy
- rolling range/structure location
- 70% Volume Profile with VAL / POC / VAH
- weighted latent edge
- logistic P(up) / P(down)
- expected value in R for a canonical 1.5R payoff
- cross-factor dispersion/conflict penalty
- data-quality adjusted confidence
- trade readiness

Core output model:

```
edge = sum(weight_i * normalized_factor_i)
p_up = sigmoid(3.2 * edge)
p_down = 1 - p_up
EV_long = 1.5 * p_up - p_down
EV_short = 1.5 * p_down - p_up
```

Execution states are `LONG`, `SHORT`, `WAIT`, or `NO TRADE`. `NO TRADE` is reserved for missing/bad data, missing volume, or extreme event-risk rather than being the default state.

## Important volume note
Spot FX and CFD metals are decentralized; there is no single centralized traded-volume tape. OANDA candle `volume` is used as tick-volume (price-update count) and is labeled as such in the UI. Crypto Binance volume is actual exchange-traded volume. True real-time COMEX gold futures volume generally requires licensed exchange data.

## Free data setup
Open **Data Keys** inside the terminal. Credentials are stored in browser `localStorage`; do not commit them to GitHub.

For XAU/FX:
1. Create an OANDA practice account/token.
2. Paste the practice token in Data Keys.
3. Run Quant Analysis.

Alternative:
1. Create a free Twelve Data Basic key.
2. Paste it in Data Keys.
3. Availability/volume varies by symbol and plan.

BTCUSD needs no key because the backend uses Binance public market data.

## Stack
- React + Vite
- FastAPI on Vercel `/api`
- pure-Python quantitative calculations (no numpy/pandas dependency required)
- provider adapters: OANDA, Twelve Data, Binance

## Vercel
Import the repository with:
- Framework: Vite
- Root directory: `./`
- Build command: `npm run build`
- Output directory: `dist`

## Safety / model validity
This is decision support, not a guarantee of profitability. A probability is only meaningful after out-of-sample calibration. Future calibration should track Brier score, realized hit-rate, EV by regime, transaction costs, spread/slippage and walk-forward performance.
