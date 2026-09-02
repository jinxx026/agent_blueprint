"""Language-light tokenization helpers supporting Chinese and Latin text."""

import re

TOKEN_PATTERN = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]", re.IGNORECASE)


def terms(text: str) -> tuple[str, ...]:
    base = TOKEN_PATTERN.findall(text.lower())
    chinese = [token for token in base if len(token) == 1 and "\u4e00" <= token <= "\u9fff"]
    bigrams = ["".join(chinese[index : index + 2]) for index in range(len(chinese) - 1)]
    return tuple(base + bigrams)
