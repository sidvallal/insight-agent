from src.utils import clean_sql, format_examples, format_schema


def test_clean_sql_strips_fences():
    assert clean_sql("```sql\nSELECT 1;\n```") == "SELECT 1;"
    assert clean_sql("```\nSELECT 1\n```") == "SELECT 1"
    assert clean_sql("  SELECT 1  ") == "SELECT 1"


def test_format_schema_includes_table_name():
    text = format_schema([{"table": "olist_orders_dataset", "content": "columns..."}])
    assert "olist_orders_dataset" in text
    assert "columns..." in text


def test_format_examples_keeps_question_and_sql():
    text = format_examples(
        [{"question": "How many orders?", "content": "Question: How many orders?\nSQL: SELECT COUNT(*) FROM o"}]
    )
    assert "How many orders?" in text
    assert "SELECT COUNT(*) FROM o" in text
