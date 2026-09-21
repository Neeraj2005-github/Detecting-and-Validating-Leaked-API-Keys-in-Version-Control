import math
from collections import Counter

FEATURE_COLUMNS = [
    "entropy",
    "length",
    "char_class_count",
    "digit_ratio",
    "repeated_char_ratio",
]


def shannon_entropy(s: str) -> float:
    """Standard Shannon entropy of the string's character distribution."""
    if not s:
        return 0.0
    counts = Counter(s)
    total = len(s)
    entropy = 0.0
    for count in counts.values():
        probability = count / total
        entropy -= probability * math.log2(probability)
    return entropy


def extract_features(matched_string: str, file_path: str, surrounding_line: str) -> dict:
    """Return a feature dict:
    - entropy: shannon_entropy(matched_string)
    - length: len(matched_string)
    - char_class_count: how many of {lower, upper, digit, symbol} appear
    - digit_ratio: fraction of characters that are digits
    - is_test_path: 1 if file_path contains 'test', 'example', 'fixture', 'mock' (case-insensitive)
    - has_example_keyword: 1 if surrounding_line contains 'example', 'sample', 'dummy', 'placeholder'
    - repeated_char_ratio: fraction of the string that is the single most common character
    """
    if matched_string is None:
        matched_string = ""
    matched_string = str(matched_string)
    lower = any(ch.islower() for ch in matched_string)
    upper = any(ch.isupper() for ch in matched_string)
    digit = any(ch.isdigit() for ch in matched_string)
    symbol = any(not ch.isalnum() for ch in matched_string)

    digit_ratio = sum(ch.isdigit() for ch in matched_string) / len(matched_string) if matched_string else 0.0
    counts = Counter(matched_string)
    repeated_char_ratio = (max(counts.values()) / len(matched_string)) if matched_string else 0.0

    file_lower = (file_path or "").lower()
    text_lower = (surrounding_line or "").lower()
    is_test_path = 1 if any(token in file_lower for token in ["test", "example", "fixture", "mock"]) else 0
    has_example_keyword = 1 if any(token in text_lower for token in ["example", "sample", "dummy", "placeholder"]) else 0

    return {
        "entropy": shannon_entropy(matched_string),
        "length": len(matched_string),
        "char_class_count": sum([lower, upper, digit, symbol]),
        "digit_ratio": digit_ratio,
        "is_test_path": is_test_path,
        "has_example_keyword": has_example_keyword,
        "repeated_char_ratio": repeated_char_ratio,
    }
