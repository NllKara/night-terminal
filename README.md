# NIGHT Quant Terminal

Personal institutional quant market intelligence terminal with live charting, realtime streams, multi-asset analysis, shipping intelligence, global indices, US/Indonesia equity desks, geopolitical/news context, AI screening and report generation.

## Production trigger
Latest production bundle includes the newest NIGHT multi-asset, equity, shipping, geopolitical, realtime-price and institutional workspace changes.

## What is live now
- TradingView interactive chart
- Realtime browser WebSocket stream for supported markets
- BTCUSD live trade stream + exchange volume from Binance
- XAU/FX/indices realtime stream through Twelve Data when the key/plan permits the symbol
- Tick-to-candle realtime quant recalculation
- Multi-timeframe quant engine
- Live shipping/AIS map
- WTI, Brent and Natural Gas board
- Live global news activity
- CFTC positioning
- FRED macro enrichment
- US Stocks desk
- Indonesia Stocks desk
- Global Indices desk
- AI Stock Screener workspace
- Fundamental Mind Map workspace
- Geopolitical and Supply Chain desk
- NIGHT AI
- Report Engine

## Quant engine
NIGHT calculates from observed market bars and contextual institutional inputs. It exposes decision outputs such as directional probability, expected value, trade readiness, confidence, regime, volume profile, flow/aggression and execution state. Internal formulas are intentionally not shown in the terminal UI.

Execution states are `LONG`, `SHORT`, `WAIT`, or `NO TRADE`. `NO TRADE` is reserved for invalid/incomplete data or extreme execution/event risk rather than being the default state.

## Data integrity
NIGHT does not silently substitute a different instrument when live data is unavailable. XAUUSD must use XAU/USD spot-style data, GBPUSD must use GBP/USD, and equivalent symbol mapping applies across the supported universe. If a realtime feed is unavailable, the UI should show that state instead of presenting a stale cross-instrument reference price.

## Important volume note
Spot FX and CFD metals are decentralized; there is no single centralized traded-volume tape. Tick/activity volume is labeled as such. Crypto Binance volume is actual exchange-traded volume.

## Stack
- React + Vite
- FastAPI on Vercel `/api`
- pure-Python quantitative calculations
- provider adapters for market, macro, news, positioning, energy and AIS data

## Vercel
Production deploys from the `main` branch.
- Framework: Vite
- Root directory: `./`
- Build command: `npm run build`
- Output directory: `dist`

## Model validity
NIGHT is decision support, not a guarantee of profitability. Probabilities and model ranks require ongoing calibration against realized outcomes.
