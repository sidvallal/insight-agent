"""Follow-up questions: conversation history, rewriting and per-turn reset."""

from langgraph.checkpoint.memory import MemorySaver

from src.graph.builder import build_graph

FIRST_SQL = "SELECT order_status, COUNT(*) FROM olist_orders_dataset GROUP BY 1"
SECOND_SQL = "SELECT order_status, COUNT(*) FROM olist_orders_dataset WHERE order_status = 'delivered' GROUP BY 1"


def make_graph():
    return build_graph(checkpointer=MemorySaver())


def thread(name="t1"):
    return {"configurable": {"thread_id": name}}


def test_follow_up_is_rewritten_using_the_previous_turn(fake_llm, fake_retrieval, fake_db):
    llm = fake_llm([
        "SQL question", FIRST_SQL, "Two statuses.",                  # turn 1: router, sql, analyst
        "Follow-up", "How many delivered orders by status?",         # turn 2: router, rewrite
        SECOND_SQL, "2 delivered.",                                  # turn 2: sql, analyst
    ])
    fake_db({FIRST_SQL: (["order_status", "count"], [["delivered", 2], ["canceled", 1]]),
             SECOND_SQL: (["order_status", "count"], [["delivered", 2]])})
    graph, config = make_graph(), thread()

    graph.invoke({"question": "Orders by status?"}, config)
    state = graph.invoke({"question": "only the delivered ones"}, config)

    rewrite_prompt = llm.prompts[4]
    assert FIRST_SQL in rewrite_prompt                      # the rewriter saw the previous SQL
    assert "only the delivered ones" in rewrite_prompt
    assert state["question"] == "How many delivered orders by status?"
    assert state["user_question"] == "only the delivered ones"
    assert state["sql"] == SECOND_SQL
    assert len(state["history"]) == 2


def test_each_turn_starts_clean(fake_llm, fake_retrieval, fake_db):
    bad = "SELECT * FROM nope"
    fake_llm(["SQL question", bad, FIRST_SQL, "ok",       # turn 1 needs one repair
              "SQL question", FIRST_SQL, "ok again"])     # turn 2 must start with retries = 0
    fake_db({bad: Exception("relation does not exist"),
             FIRST_SQL: (["order_status", "count"], [["delivered", 2]])})
    graph, config = make_graph(), thread()

    first = graph.invoke({"question": "Orders by status?"}, config)
    second = graph.invoke({"question": "Orders by status again?"}, config)

    assert first["retries"] == 1
    assert second["retries"] == 0
    assert second["error"] == ""


def test_follow_up_without_history_is_treated_as_a_new_question(fake_llm, fake_retrieval, fake_db):
    llm = fake_llm(["Follow-up", FIRST_SQL, "ok"])        # no rewrite call expected
    fake_db({FIRST_SQL: (["order_status", "count"], [["delivered", 2]])})

    state = make_graph().invoke({"question": "break that down"}, thread("empty"))

    assert state["route"] == "SQL question"
    assert len(llm.prompts) == 3


def test_threads_do_not_share_history(fake_llm, fake_retrieval, fake_db):
    fake_llm(["SQL question", FIRST_SQL, "ok", "SQL question", FIRST_SQL, "ok"])
    fake_db({FIRST_SQL: (["order_status", "count"], [["delivered", 2]])})
    graph = make_graph()

    graph.invoke({"question": "q1"}, thread("a"))
    other = graph.invoke({"question": "q2"}, thread("b"))

    assert len(other["history"]) == 1


def test_history_keeps_only_the_latest_turns(fake_llm, fake_retrieval, fake_db):
    from src import config

    turns = config.HISTORY_TURNS + 2
    fake_llm(["SQL question", FIRST_SQL, "ok"] * turns)
    fake_db({FIRST_SQL: (["order_status", "count"], [["delivered", 2]])})
    graph, cfg = make_graph(), thread("long")

    for i in range(turns):
        state = graph.invoke({"question": f"question {i}"}, cfg)

    assert len(state["history"]) == config.HISTORY_TURNS
    assert state["history"][-1]["user_question"] == f"question {turns - 1}"