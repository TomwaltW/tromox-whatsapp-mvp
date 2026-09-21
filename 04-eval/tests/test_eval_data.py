from __future__ import annotations

import pytest
from eval_testkit import make_row, write_csv

from eval.data import DataError, Sample, load_dataset
from tromox_lead import LABEL_COLUMNS, Segment


def test_sample_fields_are_exactly_the_label_columns():
    assert tuple(Sample.model_fields) == LABEL_COLUMNS


def test_loads_and_normalises(tmp_path):
    path = write_csv(tmp_path / "d.csv", [
        make_row(phone="4917604069031", product_interest="Ukko S+; mc-10", language="DE"),
        make_row(sample_id="T-002", segment="b2c", b2b_type="", b2c_intent="buy", phone="",
                 country_gold="", is_valid_lead="no", escalation_flag="TRUE", escalation_reason="human_requested"),
    ])
    dataset = load_dataset(path)
    first, second = dataset.samples
    assert first.phone == "+4917604069031" and first.country_by_phone == "DE" and first.language == "de"
    assert first.product_interest == ("MC10", "UKKO") and first.is_valid_lead is True
    assert second.segment is Segment.B2C and second.phone is None and second.country_by_phone is None
    assert second.escalation_flag is True and second.is_valid_lead is False
    assert dataset.origins == {"real": 2} and len(dataset.sha256) == 64


def test_example_rows_are_skipped(tmp_path):
    path = write_csv(tmp_path / "d.csv", [make_row(data_origin="example", sample_id="EX-1"), make_row()])
    dataset = load_dataset(path)
    assert [s.sample_id for s in dataset.samples] == ["T-001"] and dataset.skipped_examples == 1


def test_repo_labeling_template_loads_when_examples_included(eval_root):
    dataset = load_dataset(eval_root / "labeling-template.csv", include_examples=True)
    assert len(dataset.samples) >= 1
    with pytest.raises(DataError):  # only example rows -> nothing to evaluate
        load_dataset(eval_root / "labeling-template.csv")


@pytest.mark.parametrize("overrides, fragment", [
    ({"b2b_type": ""}, "requires b2b_type"),
    ({"b2c_intent": "buy"}, "b2c_intent must be blank"),
    ({"escalation_flag": "true"}, "requires escalation_reason"),
    ({"escalation_reason": "human_requested"}, "must be blank when escalation_flag=false"),
    ({"phone": "12"}, "not a possible E.164 number"),
    ({"product_interest": "Vespa"}, "unknown product code"),
    ({"segment": "dealer"}, "expected B2B, B2C or unknown"),
    ({"country_gold": "Germany"}, "alpha-2"),
    ({"conversation_text": "  "}, "must not be empty"),
    ({"escalation_flag": "maybe"}, "expected true or false"),
])
def test_invalid_rows_are_reported_with_line_numbers(tmp_path, overrides, fragment):
    path = write_csv(tmp_path / "d.csv", [make_row(**overrides)])
    with pytest.raises(DataError) as excinfo:
        load_dataset(path)
    message = str(excinfo.value)
    assert "line 2" in message and fragment in message


def test_all_problems_are_reported_at_once(tmp_path):
    path = write_csv(tmp_path / "d.csv", [make_row(b2b_type=""), make_row(sample_id="T-002", phone="12"), make_row()])
    with pytest.raises(DataError) as excinfo:
        load_dataset(path)
    assert len(excinfo.value.problems) == 2


def test_duplicate_ids_and_bad_header(tmp_path):
    path = write_csv(tmp_path / "d.csv", [make_row(), make_row()])
    with pytest.raises(DataError, match="duplicate sample_id"):
        load_dataset(path)
    bad = tmp_path / "bad.csv"
    bad.write_text("sample_id,text\n1,hello\n", encoding="utf-8")
    with pytest.raises(DataError, match="header mismatch"):
        load_dataset(bad)
