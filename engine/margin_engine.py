"""Rule-based margin engine for Trinity Macro Lens.

Every margin and P&L number comes from fixed rules in this file, never from AI.
AI only links news to products and drafts explanations of these results.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import floor, sqrt
from typing import Iterable


@dataclass(frozen=True)
class Contract:
    code: str
    price: float          # index points (S50) or THB per baht-weight (GF10)
    multiplier: float     # THB per price unit per contract
    im: float             # initial margin per contract (THB)
    mm: float             # maintenance margin per contract (THB)
    fm: float             # force margin per contract (THB)
    sigma: float          # daily volatility, decimal (EWMA)

    @property
    def notional(self) -> float:
        return self.price * self.multiplier


# S50: Trinity margin rate announcement (IM 11,795; MM 70%, FM 30% of IM); SET50 1,083.40.
S50 = Contract("S50", price=1083.40, multiplier=200, im=11_795, mm=8_256.5, fm=3_538.5, sigma=0.012)
# GF10: published broker rate (Apr 2026), to be replaced with Trinity's rate; gold 62,300 THB per baht-weight.
GF10 = Contract("GF10", price=62_300, multiplier=10, im=84_000, mm=59_040, fm=25_440, sigma=0.010)
CONTRACTS = {c.code: c for c in (S50, GF10)}


@dataclass(frozen=True)
class Account:
    account_id: str
    product: str          # "S50" or "GF10"
    contracts: int        # signed: + long, - short
    equity: float         # THB


@dataclass(frozen=True)
class Assessment:
    account_id: str
    move: float               # adverse move applied (decimal)
    pnl: float
    equity_after: float
    mm: float
    fm: float
    sigma_to_mm_now: float    # adverse σ moves before equity reaches MM today
    sigma_to_mm_after: float  # σ left above MM after the scenario
    status: str
    priority: str
    add_funds: float          # THB to restore IM after the scenario
    reduce_contracts: int     # contracts to close now to stay above MM


def ewma_volatility(returns: Iterable[float], lam: float = 0.94) -> float:
    """RiskMetrics-style EWMA volatility of daily returns (decimals)."""
    var = None
    for r in returns:
        var = r * r if var is None else lam * var + (1 - lam) * r * r
    if var is None:
        raise ValueError("need at least one return")
    return sqrt(var)


def move_to_level(c: Contract, level: float) -> float:
    """Adverse move (decimal) that takes a minimum-margin account (equity = IM) down to `level` THB."""
    return (c.im - level) / c.notional


def adverse_move(account: Account, k_sigma: float) -> float:
    """Two-sided scenario: each account is tested on the side that loses."""
    c = CONTRACTS[account.product]
    return -(1 if account.contracts > 0 else -1) * k_sigma * c.sigma


def assess(account: Account, move: float) -> Assessment:
    c = CONTRACTS[account.product]
    k = abs(account.contracts)
    side = 1 if account.contracts > 0 else -1
    im, mm, fm = c.im * k, c.mm * k, c.fm * k
    exposure = k * c.notional

    pnl = account.contracts * c.notional * move
    after = account.equity + pnl
    sig_now = (account.equity - mm) / exposure / c.sigma
    sig_after = (after - mm) / exposure / c.sigma

    if after < 0:
        status, priority = "below zero: Trinity exposed", "critical"
    elif after < fm:
        status, priority = "below FM: forced close", "critical"
    elif after < mm:
        status, priority = "below MM: margin call", "high"
    elif sig_after < 1:
        status, priority = "above MM, under 1 sigma left", "medium"
    else:
        status, priority = "safe", "low"

    add_funds = max(0.0, im - after)
    reduce = 0
    adverse = max(0.0, -side * move)
    if after < mm and adverse > 0:
        keep = floor(account.equity / (c.notional * adverse + c.mm))
        reduce = max(0, k - keep)

    return Assessment(account.account_id, move, pnl, after, mm, fm, sig_now, sig_after,
                      status, priority, add_funds, reduce)


def margin_radar(accounts: Iterable[Account], k_sigma: float) -> list[Assessment]:
    """Rank accounts by σ left above MM after the scenario, riskiest first. Risk only."""
    return sorted((assess(a, adverse_move(a, k_sigma)) for a in accounts),
                  key=lambda x: x.sigma_to_mm_after)


if __name__ == "__main__":
    print(f"S50 contract value: THB {S50.notional:,.0f} | IM {S50.im / S50.notional:.1%} | leverage ~{S50.notional / S50.im:.0f}x")
    for label, level in [("margin call (MM)", S50.mm), ("forced close (FM)", S50.fm), ("equity = 0", 0.0)]:
        print(f"  SET50 move to {label}: -{move_to_level(S50, level):.1%}")

    demo = [Account("TF-001", "S50", 1, 11_795), Account("TF-012", "GF10", 1, 72_600),
            Account("TF-008", "S50", -2, 25_949), Account("TF-027", "S50", 1, 47_180)]
    print("\nMargin Radar, two-sided ±2σ scenario:")
    for a in margin_radar(demo, 2.0):
        print(f"  {a.account_id}: move {a.move:+.1%}, equity after THB {a.equity_after:,.0f}, "
              f"{a.sigma_to_mm_after:+.2f}σ left, {a.status}")
