"""Checkpointer: lets a conversation continue across questions (and restarts)."""

from src import config


def get_checkpointer():
    """CHECKPOINTER=memory (default) keeps conversations until the program exits.
    CHECKPOINTER=postgres stores them in PostgreSQL so they survive restarts.
    """
    if config.CHECKPOINTER == "postgres":
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg import Connection
        from psycopg.conninfo import make_conninfo
        from psycopg.rows import dict_row

        url = config.database_url(readonly=False)
        conninfo = make_conninfo(
            host=url.host, port=url.port, dbname=url.database,
            user=url.username, password=url.password,
        )
        connection = Connection.connect(
            conninfo, autocommit=True, prepare_threshold=0, row_factory=dict_row
        )
        saver = PostgresSaver(connection)
        saver.setup()   # creates the checkpoint tables on first use
        return saver

    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()