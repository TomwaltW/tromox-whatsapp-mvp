"""Cost model: arithmetic sanity and freshness of generated outputs."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "03-whatsapp" / "cost_model.py"

spec = importlib.util.spec_from_file_location("cost_model", SCRIPT)
cost_model = importlib.util.module_from_spec(spec)
sys.modules["cost_model"] = cost_model
spec.loader.exec_module(cost_model)  # type: ignore[union-attr]


def _load():
    params = cost_model.load_params(ROOT / "03-whatsapp" / "cost-model-inputs.csv")
    markets = cost_model.load_markets(ROOT / "03-whatsapp" / "cost-model-rates.csv")
    return params, markets


def test_market_shares_sum_to_one_and_proxies_come_from_verified_rates():
    _, markets = _load()
    assert abs(sum(m.share for m in markets) - 1.0) < 1e-9
    weu_proxy = round((0.0550 + 0.0500 + 0.0200) / 3, 4)
    assert {m.rate_usd for m in markets if m.code in ("FR", "IT", "ES")} == {weu_proxy}


def test_mid_scenario_hand_calculation():
    params, markets = _load()
    b = cost_model.compute(params["mid"], markets)
    assert b.conversations == 900
    assert round(b.service_msgs_total) == 6174          # 4905 AI + 1269 human
    assert round(b.service_msgs_billable) == 3939       # minus 20% CTWA, minus 1,000 free
    assert b.botmaker_plan_name == "Standard" and b.botmaker_plan_usd == 149.0
    assert 360 < b.total_route_a_usd < 380


def test_monotonic_in_volume_and_free_allowance():
    params, markets = _load()
    mid = params["mid"]
    base = cost_model.compute(mid, markets).total_route_a_usd
    more = cost_model.compute(replace(mid, daily_inquiries=mid.daily_inquiries * 2), markets).total_route_a_usd
    no_free = cost_model.compute(replace(mid, free_service_msgs_per_month=0), markets).total_route_a_usd
    all_ctwa = cost_model.compute(replace(mid, ctwa_share=1.0), markets)
    assert more > base and no_free > base
    assert all_ctwa.service_msgs_billable == 0 and all_ctwa.meta_service_usd == 0


def test_plan_picker_prefers_cheapest_total():
    assert cost_model.pick_botmaker_plan(2400) == ("Standard", 149.0)
    name, cost = cost_model.pick_botmaker_plan(3600)
    assert name == "Standard" and abs(cost - 164.0) < 1e-9
    # At the published overage price, Standard + overage always beats upgrading;
    # a higher plan is justified by agent seats (10 / 20 / 50), not by volume.
    assert cost_model.pick_botmaker_plan(9000) == ("Standard", 149.0 + 6000 * 0.025)


def test_generated_outputs_are_fresh():
    result = subprocess.run([sys.executable, str(SCRIPT), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
