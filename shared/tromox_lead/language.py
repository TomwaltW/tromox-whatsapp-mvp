"""Deterministic, dependency-free language detection used as a *fallback*.

Primary source of `language` is the AI extraction; this rule-based detector covers the
webhook normaliser when the variable is missing, and keeps tests deterministic.
Returns ISO 639-1 codes, or "und" when undetermined.
"""
from __future__ import annotations

import re

_STOPWORDS: dict[str, frozenset[str]] = {
    "en": frozenset("the and you your is are do does have how what where can i we my for with price much become want would like please hello hi thanks in to of a it".split()),
    "es": frozenset("el la los las de que y en un una por para con tienen tiene quiero quisiera hola gracias precio cuanto cuánto donde dónde puedo somos soy mi es".split()),
    "de": frozenset("der die das und ich wir sie ist sind nicht ein eine für mit wie was wo kann haben möchte hallo danke preis händler bitte zu von den im".split()),
    "fr": frozenset("le la les des et je nous vous est sont un une pour avec comment quel quelle où puis avez voudrais bonjour merci prix revendeur du au en ce".split()),
    "pt": frozenset("o a os as de que e em um uma por para com tem quero gostaria olá ola obrigado obrigada preço quanto onde posso somos sou meu minha não você".split()),
    "it": frozenset("il lo la gli le di che e in un una per con come quale dove posso avete vorrei ciao buongiorno grazie prezzo rivenditore sono siamo mio non è".split()),
}
_TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ']+")
_CJK_RE = re.compile(r"[一-鿿]")
_HINT_CHARS: dict[str, str] = {"de": "äöüß", "es": "ñ¿¡", "fr": "çœêèàù", "pt": "ãõç", "it": "ìò"}


def detect_language(text: str | None) -> str:
    if not text or not text.strip():
        return "und"
    if len(_CJK_RE.findall(text)) >= 2:
        return "zh"
    lowered = text.lower()
    tokens = _TOKEN_RE.findall(lowered)
    if not tokens:
        return "und"
    scores: dict[str, float] = {}
    for lang, words in _STOPWORDS.items():
        score = float(sum(1 for t in tokens if t in words))
        score += 0.5 * sum(1 for ch in lowered if ch in _HINT_CHARS.get(lang, ""))
        scores[lang] = score
    best = max(scores, key=lambda k: (scores[k], k == "en"))
    ranked = sorted(scores.values(), reverse=True)
    if ranked[0] == 0:
        return "und"
    # Tie between two languages on very short input: prefer "und" over a coin flip.
    if len(ranked) > 1 and ranked[0] == ranked[1] and ranked[0] < 2:
        return "und"
    return best
