"""Load and validate labelled samples. Columns are exactly tromox_lead.LABEL_COLUMNS."""
from __future__ import annotations

import csv
import hashlib
import io
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from tromox_lead import (
    LABEL_COLUMNS,
    PRODUCT_CATALOG,
    B2BType,
    B2CIntent,
    EscalationReason,
    Segment,
    country_from_phone,
    normalize_e164,
    normalize_product,
)
# 别名表与清洗规则只读引用 shared 的原件（不抄一份，免得与产品目录脱节）：normalize_product 只回代码、
# 不说命中了哪个别名，金标要核对"最长别名之后还剩什么"，只能看表。
from tromox_lead.products import _ALIASES as _PRODUCT_ALIASES
from tromox_lead.products import _CLEAN_RE as _PRODUCT_CLEAN_RE

_TRUE = {"true", "1", "yes", "y", "是"}
_FALSE = {"false", "0", "no", "n", "否", ""}
# 半角 / 全角分号与逗号、顿号、斜杠、竖线都算分隔；不按空格切（别名里有空格：Ukko S+、mc10 trail x）。
_PRODUCT_SPLIT_RE = re.compile(r"[;,/|；，、]+")
# 最长别名之后允许剩下的：去掉标点后只剩年份 / 纯数字（UKKO S+ 2026、UKKO S+ (2026)）。
_PUNCT_RE = re.compile(r"[\W_]+")
_DIGITS_ONLY_RE = re.compile(r"[0-9]*")
# Excel 把号码列当成数字后的两种形态（整格匹配）：科学计数法 4.91761E+12（精度已丢），
# 以及另存时带出的小数尾巴 4917612345678.0。点号分段的正常写法（+1.202.555.0143）不在此列。
EXCEL_MANGLED_PHONE_RE = re.compile(r"\+?\d+(?:[.,]\d+)?[eE][+-]?\d+|\+?\d+\.\d+")
EXCEL_PHONE_HINT = "号码列被 Excel 当成数字改坏了；从导入批次恢复该列并设为文本格式"


def looks_excel_mangled(raw: str | None) -> bool:
    """True for phone cells Excel turned into a number: 4.91761E+12, 4917612345678.0."""
    return bool(raw) and EXCEL_MANGLED_PHONE_RE.fullmatch(str(raw).strip()) is not None


def product_code(token: str) -> str:
    """One gold product token -> catalogue code. Rejects two codes in one token and off-catalogue text.

    normalize_product() matches the longest alias prefix and ignores what follows, which is right for
    free text from a model but hides typos in gold labels: "MC10 UKKO" would read as MC10 alone and
    "MC10 Vespa" as MC10.
    """
    code = normalize_product(token)
    if code is None:
        raise ValueError(f"unknown product code {token!r} (see shared/tromox_lead/products.py)")
    key = _PRODUCT_CLEAN_RE.sub("", token.strip().lower())
    if key in _PRODUCT_ALIASES:
        return code
    alias = next(a for a in sorted(_PRODUCT_ALIASES, key=len, reverse=True) if key.startswith(a))
    rest = key[len(alias):]
    others = sorted({other for a, other in _PRODUCT_ALIASES.items() if a in rest and other != code})
    if others:
        raise ValueError(f"ambiguous product token {token!r} names {code} and {', '.join(others)}: "
                         "separate codes with ';'")
    for same in sorted((a for a, c in _PRODUCT_ALIASES.items() if c == code), key=len, reverse=True):
        rest = rest.replace(same, "")        # "Trail X MC10" is still one product
    if not _DIGITS_ONLY_RE.fullmatch(_PUNCT_RE.sub("", rest)):
        raise ValueError(f"product token {token!r} has text outside the catalogue ({rest!r}); gold labels take "
                         f"catalogue codes only ({', '.join(PRODUCT_CATALOG)}), several separated with ';'")
    return code


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
        if looks_excel_mangled(raw):
            raise ValueError(f"{raw!r}: {EXCEL_PHONE_HINT}")
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
            codes.add(product_code(token))
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
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DataError([f"{csv_path}: 不是 UTF-8 编码（第 {exc.start + 1} 个字节起无法解码）；"
                         "Excel 请另存为『CSV UTF-8（逗号分隔）』"]) from None
    # 按记录读：splitlines() 会在 U+2028 / U+0085 / \x0c 等处断行，把未加引号的单元格切成两条记录。
    reader = csv.DictReader(io.StringIO(text, newline=""))
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
    for row in reader:
        line_no = reader.line_num   # 物理行号（记录跨行时是最后一行）
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
