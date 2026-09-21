"""Prompt loading. The same file, byte for byte, must be used offline and in production."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from tromox_lead import strip_source_code

_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_BLANK_RUN_RE = re.compile(r"\n{3,}")

BUTTON_TITLES: tuple[str, ...] = ("Dealer/Distributor", "Rider or Customer", "Other")


@dataclass(frozen=True)
class PromptSpec:
    path: str
    version: str   # file stem, e.g. "classify-v1"
    sha256: str    # hash of the file as stored (before stripping comments)
    text: str      # what is actually sent as the system prompt


def strip_html_comments(text: str) -> str:
    """Remove <!-- ... --> (maintainer notes and GENERATED markers) and tidy blank lines."""
    return _BLANK_RUN_RE.sub("\n\n", _COMMENT_RE.sub("", text)).strip() + "\n"


def load_prompt(path: str | Path) -> PromptSpec:
    prompt_path = Path(path)
    raw = prompt_path.read_bytes()
    text = strip_html_comments(raw.decode("utf-8"))
    if "BEGIN GENERATED" in text or not text.strip():
        raise ValueError(f"prompt {prompt_path} is empty or still contains generator markers")
    return PromptSpec(path=str(prompt_path), version=prompt_path.stem,
                      sha256=hashlib.sha256(raw).hexdigest(), text=text)


def build_user_message(conversation_text: str, button_choice: str | None = None) -> str:
    """Format one enquiry for the model.

    The source short code ([IG-2609]) is parsed by rule elsewhere and removed here. The phone
    country is deliberately NOT given to the model: country comes from the phone prefix rule.
    """
    choice = button_choice if button_choice in BUTTON_TITLES else "none"
    body = strip_source_code(conversation_text) or conversation_text.strip()
    return f"<button_choice>{choice}</button_choice>\n<conversation>\n{body}\n</conversation>"
