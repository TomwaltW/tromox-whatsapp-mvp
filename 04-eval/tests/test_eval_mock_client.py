from __future__ import annotations

from pathlib import Path

import pytest

from eval.clients import DEFAULT_SEED, MockClient, build_client
from eval.data import load_dataset
from eval.metrics import evaluate
from eval.prompt import load_prompt
from eval.run import run_eval


@pytest.fixture(scope="module")
def synthetic():
    base = Path(__file__).resolve().parents[1]
    return load_dataset(base / "synthetic-samples.csv"), load_prompt(base / "prompts" / "classify-v1.md")


def _texts(client, dataset, prompt):
    return [client.complete(prompt.text, s.conversation_text, sample=s).text for s in dataset.samples]


def test_same_seed_gives_identical_output(synthetic):
    dataset, prompt = synthetic
    assert _texts(MockClient(), dataset, prompt) == _texts(MockClient(seed=DEFAULT_SEED), dataset, prompt)
    assert _texts(MockClient(seed=1), dataset, prompt) != _texts(MockClient(seed=2), dataset, prompt)


def test_zero_error_rate_reproduces_the_gold_labels(synthetic):
    dataset, prompt = synthetic
    r = evaluate(run_eval(list(dataset.samples), prompt, MockClient(error_rate=0.0), progress=False))
    assert r.parse_success == 1.0 and r.b2b_recall == 1.0 and r.b2b_precision == 1.0
    assert r.country_accuracy == 1.0 and r.product_recognition == 1.0
    assert r.escalation_pred == r.escalation_gold == r.escalation_tp == r.escalation_reason_match


def test_default_mock_is_imperfect_but_keeps_b2b_recall(synthetic):
    dataset, prompt = synthetic
    r = evaluate(run_eval(list(dataset.samples), prompt, MockClient(), progress=False))
    assert 0.90 <= r.b2b_recall < 1.0
    assert r.parse_ok < r.n_total            # the demo report shows at least one parse failure
    assert r.escalation_rate <= 0.30


def test_mock_needs_the_sample_and_validates_error_rate():
    with pytest.raises(ValueError):
        MockClient(error_rate=1.5)
    with pytest.raises(ValueError):
        MockClient().complete("sys", "user")


def test_factory():
    assert isinstance(build_client("mock", seed=3, error_rate=0.1), MockClient)
    for bad in ("gpt-4", "openai:", "anthropic:", "mock:extra", ""):
        with pytest.raises(ValueError):
            build_client(bad)
