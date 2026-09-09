# Trail B — The Speculator's Morning

A daily discretionary "trader agent" journal: a $100,000 paper book, run
once per weekday morning by Claude against `PLAYBOOK.md` (read-only). It
reads the regime, tape, calendar, and crowd hype, then logs a
`long/short/flat` call per watchlist instrument to `ledger.csv` with an
explicit invalidation level. `score.py` resolves expired calls against
yfinance daily bars and grades the trail.

## Files
`ledger.csv` (append-only calls), `watchlist.txt`/`voices.txt`/`calendar.md`
(daily-read inputs), `journal/YYYY-MM-DD.md` (morning notes), `score.py` +
`resolved.csv` + `SCORECARD.md` (scoring), `run_daily.sh` (entry point),
`logs/YYYY-MM-DD.log` (run output), `com.trailb.trader.plist` (launchd job,
not installed).

## Run once, manually
```
bash trader-agent/run_daily.sh
uv run --with pandas --with yfinance --with numpy python trader-agent/score.py
```

## Install / uninstall the scheduled job (Mon-Fri, 07:30 America/New_York)
```
cp trader-agent/com.trailb.trader.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.trailb.trader.plist
```
```
launchctl unload ~/Library/LaunchAgents/com.trailb.trader.plist
rm ~/Library/LaunchAgents/com.trailb.trader.plist
```
Hour/Minute in the plist are LOCAL time, computed for this machine's
detected zone (CDT) — check the comment inside before installing elsewhere.

## Stop rule
After 60 resolved non-flat calls or 6 months (whichever first): if Brier
isn't below 0.25 with a 90% bootstrap CI excluding 0.25, or Sharpe < 0.5,
shut down or revise once in a dated PLAYBOOK v2. No v3.
