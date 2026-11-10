from margin_engine import GF10, S50, Account, adverse_move, assess, ewma_volatility, margin_radar, move_to_level


def test_s50_contract_and_leverage():
    assert round(S50.notional) == 216_680
    assert round(S50.im / S50.notional * 100, 1) == 5.4
    assert round(S50.notional / S50.im) == 18


def test_s50_thresholds_match_the_deck():
    assert round(move_to_level(S50, S50.mm) * 100, 1) == 1.6   # margin call
    assert round(move_to_level(S50, S50.fm) * 100, 1) == 3.8   # forced close
    assert round(move_to_level(S50, 0.0) * 100, 1) == 5.4      # initial margin used up


def test_gf10_alert_example_from_the_deck():
    # "If gold falls 2% after tonight's US CPI, your GF10 equity would sit only THB 1,100 above the margin call level."
    a = Account("TF-012", "GF10", 1, 72_600)
    r = assess(a, adverse_move(a, 2.0))
    assert round(r.move, 3) == -0.02
    assert round(r.equity_after - r.mm) == 1_100
    assert r.priority == "medium"


def test_two_sided_scenario_hits_shorts_on_the_upside():
    long_, short = Account("L", "S50", 1, S50.im), Account("S", "S50", -1, S50.im)
    assert adverse_move(long_, 2.0) < 0 < adverse_move(short, 2.0)
    assert assess(short, adverse_move(short, 2.0)).status.startswith("below MM")


def test_status_ladder():
    a = Account("A", "S50", 1, S50.im)
    assert assess(a, -0.010).priority == "medium"
    assert assess(a, -0.020).status.startswith("below MM")
    assert assess(a, -0.045).status.startswith("below FM")
    assert assess(a, -0.060).status.startswith("below zero")


def test_reduce_contracts_keeps_account_above_mm():
    a = Account("B", "S50", 4, 4 * S50.im)
    r = assess(a, -0.03)
    kept = 4 - r.reduce_contracts
    assert 0 < r.reduce_contracts <= 4
    if kept:
        assert a.equity - kept * S50.notional * 0.03 >= kept * S50.mm


def test_radar_ranks_by_risk_only():
    accts = [Account("safe", "S50", 1, 4 * S50.im), Account("thin", "S50", 1, S50.im), Account("gold", "GF10", 1, 72_600)]
    assert [x.account_id for x in margin_radar(accts, 2.0)][0] == "thin"


def test_ewma_constant_returns():
    assert abs(ewma_volatility([0.01] * 50) - 0.01) < 1e-12
