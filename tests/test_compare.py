from datetime import datetime
from decimal import Decimal

from eval.compare import results_match


def test_column_aliases_are_ignored():
    assert results_match([{"average_price": 120.65}], [{"average_product_price": 120.65}])


def test_row_order_is_ignored():
    assert results_match([[1, "a"], [2, "b"]], [[2, "b"], [1, "a"]])


def test_decimal_float_and_int_are_equivalent():
    assert results_match([[Decimal("12.50"), 3]], [[12.5, 3.0]])


def test_small_float_noise_is_ignored():
    assert results_match([[12.5001]], [[12.5]])


def test_different_values_do_not_match():
    assert not results_match([[1]], [[2]])


def test_extra_column_does_not_match():
    assert not results_match([["o1", "p1", 10.0]], [["o1", 10.0]])


def test_different_row_count_does_not_match():
    assert not results_match([[1], [2]], [[1]])


def test_none_values_are_compared():
    assert results_match([["x", None]], [["x", None]])
    assert not results_match([["x", None]], [["x", 5]])


def test_dates_compare_as_iso_strings():
    assert results_match([[datetime(2018, 1, 1)]], [["2018-01-01T00:00:00"]])


def test_missing_result_never_matches():
    assert not results_match(None, [[1]])
