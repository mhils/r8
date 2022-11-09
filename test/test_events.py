import pytest

from r8.cli.events import format_untrusted_col
from r8.cli.events import min_distinguishable_column_width
from r8.cli.events import wcswidth


def test_format_untrusted_col_simple():
    assert format_untrusted_col(None, 5) == "-    "
    assert format_untrusted_col("x", 5) == "x    "
    assert format_untrusted_col("1234567", 5) == "12345"


def test_format_untrusted_col_escape_chars():
    assert format_untrusted_col("\x07", 5) == "␇    "


@pytest.mark.skipif(wcswidth is len, reason="requires wcwidth")
def test_format_untrusted_col_emoji():
    assert format_untrusted_col("😃", 5) == "😃   "
    assert format_untrusted_col("😃😃😃😃😃😃😃", 6) == "😃😃😃"
    assert format_untrusted_col("😃😃😃😃😃😃😃", 5) == "😃😃 "


def test_min_distinguishable_column_width():
    assert min_distinguishable_column_width(["a", "b", "c"]) == 1
    assert min_distinguishable_column_width(["aa", "ab", "ac"]) == 2
    assert min_distinguishable_column_width(["123", "1234", "def"]) == 4
