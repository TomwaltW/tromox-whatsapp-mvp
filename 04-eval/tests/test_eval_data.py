from __future__ import annotations

import pytest
from eval_testkit import make_row, write_csv

from eval.data import DataError, Sample, load_dataset, looks_excel_mangled, product_code
from tromox_lead import LABEL_COLUMNS, Segment
from tromox_lead.products import _ALIASES


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


# --- gold products: separators, one code per token, catalogue only ---------------------------------

def _products(value: str) -> tuple[str, ...]:
    return Sample.model_validate(make_row(product_interest=value)).product_interest


@pytest.mark.parametrize("value", ["MC10；UKKO", "MC10/UKKO", "MC10|UKKO", "MC10、UKKO", "MC10，UKKO", "MC10; UKKO", "UKKO,mc-10"])
def test_products_split_on_half_and_full_width_separators(value):
    assert _products(value) == ("MC10", "UKKO")


@pytest.mark.parametrize("value, code", [
    ("UKKO S+ 2026", "UKKO"), ("mc10 trail x", "MC10"), ("MINO B", "MINO"), ("M05 Pro", "M05"),
    ("Ukko S+", "UKKO"), ("mc-10", "MC10"), ("UKKO S+ (2026)", "UKKO"),
])
def test_single_product_spellings_still_load_as_one_code(value, code):
    assert _products(value) == (code,)


@pytest.mark.parametrize("value, fragment", [
    ("MC10 UKKO", "ambiguous product token 'MC10 UKKO'"),      # read as MC10 alone before
    ("UKKO S+ M05", "ambiguous product token 'UKKO S+ M05'"),
    ("MC10 Vespa", "outside the catalogue ('vespa')"),         # read as MC10 before
])
def test_two_codes_in_one_token_or_off_catalogue_text_is_reported(tmp_path, value, fragment):
    path = write_csv(tmp_path / "d.csv", [make_row(product_interest=value)])
    with pytest.raises(DataError) as excinfo:
        load_dataset(path)
    message = str(excinfo.value)
    assert "line 2" in message and fragment in message and "';'" in message


def test_every_alias_in_the_shared_table_is_one_product():
    assert {alias: product_code(alias) for alias in _ALIASES} == _ALIASES


# --- phone column mangled by Excel ---------------------------------------------------------------

@pytest.mark.parametrize("raw", ["4.91761E+12", "4917612345678.0", "4,91761E+12", "+4917612345678.0"])
def test_excel_mangled_phone_is_a_data_error(tmp_path, raw):
    path = write_csv(tmp_path / "d.csv", [make_row(phone=raw)])
    with pytest.raises(DataError) as excinfo:
        load_dataset(path)
    message = str(excinfo.value)
    assert "line 2" in message and "Excel" in message and "文本格式" in message


@pytest.mark.parametrize("raw, e164", [
    ("+4917612345678", "+4917612345678"), ("4917612345678", "+4917612345678"),
    ("+49 176 1234 5678", "+4917612345678"), ("+1.202.555.0143", "+12025550143"),   # dots as separators are fine
])
def test_phone_written_as_text_still_loads(raw, e164):
    assert not looks_excel_mangled(raw)
    assert Sample.model_validate(make_row(phone=raw)).phone == e164


# --- CSV is read by record, not by str.splitlines() ----------------------------------------------

@pytest.mark.parametrize("sep", ["\u2028", "\u2029", "\x85", "\x0b", "\x0c", "\x1c", "\x1e"])
def test_line_separator_characters_inside_an_unquoted_cell_keep_the_record_whole(tmp_path, sep):
    text = f"first part{sep}second part"
    path = write_csv(tmp_path / "d.csv", [make_row(conversation_text=text), make_row(sample_id="T-002")])
    assert f'"first part{sep}' not in path.read_text(encoding="utf-8")        # the csv writer leaves it unquoted
    dataset = load_dataset(path)
    assert [s.sample_id for s in dataset.samples] == ["T-001", "T-002"]
    assert dataset.samples[0].conversation_text == text


def test_line_numbers_are_physical_lines_after_a_multiline_cell(tmp_path):
    path = write_csv(tmp_path / "d.csv", [make_row(conversation_text="line one\nline two"),
                                          make_row(sample_id="T-002", phone="12")])
    with pytest.raises(DataError) as excinfo:
        load_dataset(path)
    assert "line 4 (T-002)" in str(excinfo.value)


def test_non_utf8_file_is_a_data_error_that_names_the_fix(tmp_path):
    utf8 = write_csv(tmp_path / "d.csv", [make_row(conversation_text="你好，我们想做经销商，请问价格")])
    gbk = tmp_path / "gbk.csv"
    gbk.write_bytes(utf8.read_text(encoding="utf-8").encode("gbk", errors="replace"))
    with pytest.raises(DataError) as excinfo:
        load_dataset(gbk)
    assert "不是 UTF-8 编码" in str(excinfo.value) and "CSV UTF-8" in str(excinfo.value)
