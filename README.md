# Trinity Macro Lens for TFEX

Know the risk before the call. Macro Lens shows Trinity's team and its TFEX clients what tonight's market event could do to each account's margin, before the market moves.

**Live:** https://pakwounp.github.io/trinitymacrolens/

> All accounts, the event calendar, news and market data on this page are simulated. No client data is used. Scenarios are what-if calculations, not forecasts, and not investment advice.

## Three views

| View | For | What it does |
| --- | --- | --- |
| **Event review** | Risk analyst | Monitors scheduled events, market factors and news. AI links an event to the TFEX products it can move; the analyst sets a two-sided stress scenario and approves it once for every account. |
| **Margin Radar** | Trinity risk team | Ranks every account by how close tonight's scenario takes it to maintenance margin. Call list before the open, a reason per account, follow-up status and an audit trail. |
| **Client app** | TFEX clients | Position Brief: the client's own buffer, what-if scenarios and options (add funds, pledge stock, reduce, hold). |

The page works on desktop and on iPhone.

## How a run works

1. **Monitor signals.** Economic calendar, market factors, overnight headlines. Unsourced or stale news (older than 24 h) is held, not used.
2. **Select relevant events.** AI shortlists the TFEX products an event can move. AI sees news and product lists only, never client accounts. An analyst approves each event once.
3. **Size the move.** Daily σ per product by EWMA (λ 0.94). The scenario is two-sided (±1σ, ±2σ, past similar events, or custom), and each account is tested on the side that loses.
4. **Assess each account.** Rule-based code computes P&L and equity against MM and FM. Ranking is by risk only, never by commission or client value.
5. **Explain and compare.** AI drafts one explanation per event; code fills in each account's numbers; message templates are approved by Compliance. Clients see risk and options, not buy or sell advice.

Runs before the market closes and again before the open. If Macro Lens is unavailable, margin calls run exactly as today.

## Margin rules (code, not AI)

| Product | Price | Contract value | IM | MM | FM | Daily σ |
| --- | --- | --- | --- | --- | --- | --- |
| SET50 Index Futures (S50) | 1,083.40 pts × 200 | THB 216,680 | 11,795 | 8,256.5 | 3,538.5 | 1.2% |
| 10 Baht Gold Futures (GF10) | 62,300 THB/baht × 10 | THB 623,000 | 84,000 | 59,040 | 25,440 | 1.0% |

S50 margin follows Trinity's margin rate announcement (MM 70%, FM 30% of IM). GF10 margin uses a published broker rate (April 2026) until Trinity's rate is loaded.

At minimum margin on S50, a move against the position of **1.6%** reaches MM (margin call), **3.8%** reaches FM (forced close), and **5.4%** uses up the initial margin.

For each account:

```
P&L            = contracts × price × multiplier × move
Equity after   = equity + P&L
σ to MM        = (equity − MM) ÷ (|contracts| × contract value) ÷ σ
Priority       = critical (below FM) · high (below MM) · medium (under 1σ left) · low
```

## Traceability

Every alert record keeps the event and its source, the news used and its publish time, the approved scenario, the approver and time, the margin rates and the calculation. Client alerts are capped at one per event and three per week.

## Repository

```
index.html                     the application (single self-contained page)
engine/margin_engine.py        rule-based margin engine, EWMA volatility, two-sided scenario
engine/test_margin_engine.py   tests that reproduce the published thresholds
```

```bash
cd engine
python3 margin_engine.py
python3 -m pytest -q
```

## Rollout

1. **Prototype:** replay one real event night with simulated accounts, real margin rates and real prices.
2. **Check:** back-test past event nights (alert before the margin call? by how many hours? missed cases and false alarms), stale-price handling, analyst and compliance review.
3. **Pilot:** half the TFEX team for three months, staff view first, measured against a matched other half: forced closes per 1,000 accounts, share of alerted clients taking timely action, revenue per staff member.
4. **Later:** a predictive ML model, adopted only if back-tests show it beats the rules.
