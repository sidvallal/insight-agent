"""Groq LLM configuration for the Text-to-SQL project."""

import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def get_llm() -> ChatGroq:
    """Initialize and return the Groq chat model."""

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from the .env file.")

    return ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0,
        api_key=api_key,
    )


if __name__ == "__main__":
    llm = get_llm()
    response = llm.invoke("Reply with exactly: Groq connection successful")
    print(response.content)