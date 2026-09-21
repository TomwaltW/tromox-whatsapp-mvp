"""Load and validate labelled samples. Columns are exactly tromox_lead.LABEL_COLUMNS."""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from tromox_lead import (
    LABEL_COLUMNS,
    B2BType,
    B2CIntent,
    EscalationReason,
    Segment,
    country_from_phone,
    normalize_e164,
    normalize_product,
)

_TRUE = {"true", "1", "yes", "y", "是"}
_FALSE = {"false", "0", "no", "n", "否", ""}
_PRODUCT_SPLIT_RE = re.compile(r"[;,]+")


class DataError(ValueError):
    """Raised with every row problem at once, so annotators fix the file in one pass."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("invalid labelled data:\n  " + "\n  ".join(problems))


def _blank_to_none(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class Sample(BaseModel):
    """One labelled enquiry. Gold labels follow 04-eval/labeling-guide.md."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sample_id: str
    data_origin: Literal["real", "synthetic", "example"]
    phone: str | None = None
    conversation_text: str
    language: str
    segment: Segment
    b2b_type: B2BType | None = None
    b2c_intent: B2CIntent | None = None
    country_gold: str | None = None
    product_interest: tuple[str, ...] = ()
    escalation_flag: bool = False
    escalation_reason: EscalationReason | None = None
    is_valid_lead: bool | None = None
    annotator: str | None = None
    label_notes: str | None = None

    @field_validator("sample_id", "conversation_text", mode="before")
    @classmethod
    def _required_text(cls, v: Any) -> str:
        text = "" if v is None else str(v).strip()
        if not text:
            raise ValueError("must not be empty")
        return text

    @field_validator("phone", mode="before")
    @classmethod
    def _phone(cls, v: Any) -> str | None:
        raw = _blank_to_none(v)
        if raw is None:
            return None
        e164 = normalize_e164(raw)
        if e164 is None:
            raise ValueError(f"not a possible E.164 number: {raw!r}")
        return e164

    @field_validator("language", mode="before")
    @classmethod
    def _language(cls, v: Any) -> str:
        text = (_blank_to_none(v) or "").lower()
        if not re.fullmatch(r"[a-z]{2,3}", text):
            raise ValueError("expected an ISO 639-1 code such as en, de, es (or und)")
        return text

    @field_validator("segment", mode="before")
    @classmethod
    def _segment(cls, v: Any) -> str:
        text = (_blank_to_none(v) or "").strip()
        upper = text.upper()
        if upper in ("B2B", "B2C"):
            return upper
        if text.lower() == "unknown":
            return "unknown"
        raise ValueError("expected B2B, B2C or unknown")

    @field_validator("b2b_type", "b2c_intent", "escalation_reason", mode="before")
    @classmethod
    def _enum(cls, v: Any) -> Any:
        text = _blank_to_none(v)
        return text.lower() if isinstance(text, str) else text

    @field_validator("country_gold", mode="before")
    @classmethod
    def _country(cls, v: Any) -> str | None:
        text = _blank_to_none(v)
        if text is None:
            return None
        text = text.upper()
        if not re.fullmatch(r"[A-Z]{2}", text):
            raise ValueError("expected an ISO 3166-1 alpha-2 code such as DE")
        return text

    @field_validator("product_interest", mode="before")
    @classmethod
    def _products(cls, v: Any) -> tuple[str, ...]:
        if v is None:
            return ()
        tokens = _PRODUCT_SPLIT_RE.split(v) if isinstance(v, str) else list(v)
        codes: set[str] = set()
        for token in tokens:
            token = str(token).strip()
            if not token:
                continue
            code = normalize_product(token)
            if code is None:
                raise ValueError(f"unknown product code {token!r} (see shared/tromox_lead/products.py)")
            codes.add(code)
        return tuple(sorted(codes))

    @field_validator("escalation_flag", mode="before")
    @classmethod
    def _flag(cls, v: Any) -> bool:
        text = str(v if v is not None else "").strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise ValueError("expected true or false")

    @field_validator("is_valid_lead", mode="before")
    @classmethod
    def _valid_lead(cls, v: Any) -> bool | None:
        text = str(v if v is not None else "").strip().lower()
        if text == "":
            return None
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise ValueError("expected yes, no or blank")

    @field_validator("annotator", "label_notes", mode="before")
    @classmethod
    def _optional_text(cls, v: Any) -> str | None:
        return _blank_to_none(v)

    @model_validator(mode="after")
    def _consistency(self) -> "Sample":
        if self.segment is Segment.B2B and self.b2b_type is None:
            raise ValueError("segment=B2B requires b2b_type (use 'other' when none fits)")
        if self.segment is not Segment.B2B and self.b2b_type is not None:
            raise ValueError("b2b_type must be blank unless segment=B2B")
        if self.segment is Segment.B2C and self.b2c_intent is None:
            raise ValueError("segment=B2C requires b2c_intent (use 'other' when none fits)")
        if self.segment is not Segment.B2C and self.b2c_intent is not None:
            raise ValueError("b2c_intent must be blank unless segment=B2C")
        if self.escalation_flag and self.escalation_reason is None:
            raise ValueError("escalation_flag=true requires escalation_reason")
        if not self.escalation_flag and self.escalation_reason is not None:
            raise ValueError("escalation_reason must be blank when escalation_flag=false")
        return self

    @property
    def country_by_phone(self) -> str | None:
        return country_from_phone(self.phone)


class Dataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    sha256: str
    samples: tuple[Sample, ...]
    skipped_examples: int = 0

    @property
    def origins(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for sample in self.samples:
            counts[sample.data_origin] = counts.get(sample.data_origin, 0) + 1
        return counts


def _first_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "row"
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


def load_dataset(path: str | Path, *, include_examples: bool = False) -> Dataset:
    """Read a labelled CSV. Rows with data_origin=example are template rows and are skipped."""
    csv_path = Path(path)
    raw = csv_path.read_bytes()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines(keepends=True))
    header = tuple(reader.fieldnames or ())
    problems: list[str] = []
    missing = [c for c in LABEL_COLUMNS if c not in header]
    extra = [c for c in header if c not in LABEL_COLUMNS]
    if missing or extra:
        raise DataError([f"header mismatch - missing: {missing or '-'}, unexpected: {extra or '-'}; "
                         f"expected exactly: {', '.join(LABEL_COLUMNS)}"])

    samples: list[Sample] = []
    seen: dict[str, int] = {}
    skipped = 0
    for line_no, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        try:
            sample = Sample.model_validate({k: row.get(k) for k in LABEL_COLUMNS})
        except ValidationError as exc:
            problems.append(f"line {line_no} ({row.get('sample_id') or '?'}): {_first_error(exc)}")
            continue
        if sample.data_origin == "example" and not include_examples:
            skipped += 1
            continue
        if sample.sample_id in seen:
            problems.append(f"line {line_no}: duplicate sample_id {sample.sample_id!r} (first seen on line {seen[sample.sample_id]})")
            continue
        seen[sample.sample_id] = line_no
        samples.append(sample)
    if problems:
        raise DataError(problems)
    if not samples:
        raise DataError(["no usable rows (example rows are skipped)"])
    return Dataset(path=str(csv_path), sha256=hashlib.sha256(raw).hexdigest(), samples=tuple(samples),
                   skipped_examples=skipped)
