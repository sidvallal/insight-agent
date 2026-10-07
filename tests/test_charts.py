from src.charts import suggest_chart


def test_text_and_number_gives_a_bar_chart():
    chart = suggest_chart(["status", "orders"], [["delivered", 10], ["canceled", 2]], "Orders by status")
    assert chart["data"][0]["type"] == "bar"
    assert chart["data"][0]["x"] == ["delivered", "canceled"]


def test_bars_are_sorted_and_limited_to_the_top_20():
    rows = [[f"c{i}", i] for i in range(50)]
    chart = suggest_chart(["category", "n"], rows)
    assert len(chart["data"][0]["x"]) == 20
    assert chart["data"][0]["y"][0] == 49


def test_dates_give_a_line_chart_sorted_by_date():
    rows = [["2018-02-01", 5], ["2018-01-01", 3]]
    chart = suggest_chart(["month", "orders"], rows)
    assert chart["data"][0]["type"] == "scatter"
    assert chart["data"][0]["x"] == ["2018-01-01", "2018-02-01"]


def test_several_numeric_columns_give_several_lines():
    rows = [["2018-01-01", 3, 1.5], ["2018-02-01", 5, 2.5]]
    assert len(suggest_chart(["month", "orders", "avg"], rows)["data"]) == 2


def test_single_value_or_single_row_has_no_chart():
    assert suggest_chart(["n"], [[5]]) is None
    assert suggest_chart(["status", "n"], [["delivered", 5]]) is None


def test_text_only_result_has_no_chart():
    assert suggest_chart(["a", "b"], [["x", "y"], ["z", "w"]]) is None


def test_none_values_do_not_crash():
    chart = suggest_chart(["status", "n"], [["a", None], ["b", 4], ["c", 2]])
    assert chart["data"][0]["x"][0] == "b"


def test_figure_spec_is_valid_plotly():
    import pytest

    go = pytest.importorskip("plotly.graph_objects")
    chart = suggest_chart(["status", "n"], [["a", 1], ["b", 2]], "t")
    assert go.Figure(chart) is not None