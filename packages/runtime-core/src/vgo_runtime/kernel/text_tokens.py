from __future__ import annotations

import re
from typing import Any, Iterable


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
HAN_RUN_PATTERN = re.compile(r"[\u3400-\u9fff]+")
DEFAULT_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "for",
        "from",
        "into",
        "the",
        "then",
        "this",
        "that",
        "with",
    }
)
SKILL_MATCH_STOPWORDS = frozenset((*DEFAULT_STOPWORDS, "user", "needs", "help"))
BENCHMARK_STOPWORDS = frozenset((*SKILL_MATCH_STOPWORDS, "produce"))


def token_variants(token: str) -> set[str]:
    variants = {token}
    if len(token) > 4 and token.endswith("ies"):
        variants.add(token[:-3] + "y")
    elif len(token) > 3 and token.endswith("s"):
        variants.add(token[:-1])
    if len(token) > 5 and token.endswith("ing"):
        variants.add(token[:-3])
    return variants


def tokens_from_text(
    text: str,
    *,
    stopwords: Iterable[str] = DEFAULT_STOPWORDS,
    stem: bool = False,
    min_length: int = 3,
    include_han: bool = False,
) -> set[str]:
    blocked = frozenset(stopwords)
    tokens: set[str] = set()
    for token in TOKEN_PATTERN.findall(text.lower()):
        if len(token) < min_length or token in blocked:
            continue
        if stem:
            tokens.update(token_variants(token))
        else:
            tokens.add(token)
    # Kernel discovery opts in; semantic-router scoring keeps its existing vocabulary.
    if include_han:
        for run in HAN_RUN_PATTERN.findall(text):
            tokens.update(
                token for index in range(len(run) - 1)
                if (token := run[index:index + 2]) not in blocked
            )
    return tokens


def tokens_from_values(
    values: Any,
    *,
    stopwords: Iterable[str] = DEFAULT_STOPWORDS,
    stem: bool = False,
    min_length: int = 3,
    include_han: bool = False,
) -> set[str]:
    if isinstance(values, list):
        return tokens_from_text(
            " ".join(str(value) for value in values),
            stopwords=stopwords,
            stem=stem,
            min_length=min_length,
            include_han=include_han,
        )
    return set()


def expand_tokens(tokens: tuple[str, ...]) -> set[str]:
    expanded: set[str] = set()
    for token in tokens:
        expanded.update(token_variants(token))
    return expanded
