# Failure analysis (legacy v3 run, held-out 30 questions)

8 of 30 held-out questions failed. Only one is a clear model mistake; the rest were
ambiguous questions, now clarified in `eval/questions.json`.

| ID | What happened | Cause | Status |
|---|---|---|---|
| E019 | Returned an extra `product_id` column | Ambiguous question | Question now names the columns |
| E020 | Heaviest products came back with NULL weights | PostgreSQL sorts NULLs first on `DESC`; model missed `IS NOT NULL` | Question now says to ignore missing weights. Good candidate for a prompt rule or a few-shot example |
| M012 | No `LIMIT 10` | Ambiguous question | Question now says "top 10" |
| M014, H006 | Used English category names (via the translation table) instead of the Portuguese ones | Gold uses the raw column; the model's answer is arguably better | Question now says to use the original name |
| H007, H010 | Revenue computed from `payment_value`, gold uses item `price` | "Revenue" is undefined; payments also include a month with no items (25 vs 24 rows) | Question now defines revenue |
| H009 | Grouped by `customer_id` instead of `customer_unique_id`, so every customer shows 1 order | Real modeling error: needs a join to `customers` | Question now names `customer_unique_id`. Genuine hard case, keep for the interview story |

## Bugs found while reviewing (all fixed)

1. **Benchmark leakage:** 20 of the 50 questions, with their exact gold SQL, were in the few-shot store, so v2/v3 looked better than they were. Evaluation now excludes each question's own example.
2. **Unfair comparison:** the v3 evaluator compared column names, so a correct answer with a different alias failed (6 of the 14 "failures"). That is why v3 looked worse than v2. Comparison is now values-only for every version.
3. **Missing table names in the graph:** schema chunks do not contain their table name and the graph nodes sent only the chunk text. The table name is now added to prompts and to the embedded text.
4. **Out-of-scope questions** were sent to the analyst LLM with no data. They now go to a refuse node.
5. **Router** silently refused valid questions if the label had different case or punctuation. Parsing is now tolerant and defaults to "SQL question".
6. **Empty results** were never retried. One repair attempt is now allowed.
7. **Analyst** was not told when it only saw the first 20 rows of a larger result.
8. A new DB engine and Hugging Face client were created on every call. They are now shared.
9. `import_data.py` appended duplicate rows on every re-run. It now refuses unless `--reset` is used.
