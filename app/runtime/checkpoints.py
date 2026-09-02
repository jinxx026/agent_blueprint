"""Checkpoint factory kept separate so durable storage can replace memory later."""

from langgraph.checkpoint.memory import InMemorySaver


def create_checkpointer() -> InMemorySaver:
    """Keep conversation state by thread ID for the lifetime of this process."""

    return InMemorySaver()
