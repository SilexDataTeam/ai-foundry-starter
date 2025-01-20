# Copyright 2025 Silex Data Solutions dba Data Science Technologies, LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langgraph.graph import END, MessagesState, StateGraph
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger("rag_qa")

# Initialize model information
MODEL_GATEWAY_BASE_URL = os.getenv("MODEL_GATEWAY_BASE_URL")
MODEL_GATEWAY_MODEL_ID = os.getenv("MODEL_GATEWAY_MODEL_ID")
EMBEDDING_MODEL_ID = os.getenv("EMBEDDING_MODEL_ID")

if MODEL_GATEWAY_MODEL_ID is None:
    logger.error("MODEL_GATEWAY_MODEL_ID is not set")
    raise Exception("MODEL_GATEWAY_MODEL_ID is not set")

if EMBEDDING_MODEL_ID is None:
    logger.error("EMBEDDING_MODEL_ID is not set")
    raise Exception("EMBEDDING_MODEL_ID is not set")

# Initalize DB information
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

if not DB_USER:
    logging.error("DB_USER is not set")
    raise Exception("DB_USER is not set")

if not DB_PASSWORD:
    logging.error("DB_PASSWORD is not set")
    raise Exception("DB_PASSWORD is not set")

if not DB_HOST:
    logging.error("DB_HOST is not set")
    raise Exception("DB_HOST is not set")

if not DB_NAME:
    logging.error("DB_NAME is not set")
    raise Exception("DB_NAME is not set")

# Initialize collection
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

if not COLLECTION_NAME:
    logging.error("COLLECTION_NAME is not set")
    raise Exception("COLLECTION_NAME is not set")

embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL_ID)

engine = create_async_engine(
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=COLLECTION_NAME,
    connection=engine,
)

llm = ChatOpenAI(
    model=MODEL_GATEWAY_MODEL_ID,
    base_url=MODEL_GATEWAY_BASE_URL,
    temperature=0,
    streaming=True,
)


def retrieve_documents(query: str) -> list[tuple[Document, float]]:
    """Retrieve relevant documents based on the query."""
    try:
        results = vector_store.similarity_search_with_score(query, k=5)
        logger.info("Retrieved documents: %s", results)
        if not results:
            logger.warning("No documents retrieved for query: %s", query)
        return results
    except Exception as e:
        logger.error("Error retrieving documents: %s", e)
        raise


def call_model(state: MessagesState, config: RunnableConfig) -> dict[str, BaseMessage]:
    """Calls the language model and returns the response."""
    system_message = """You are a helpful assistant."""

    user_query = state["messages"][-1].content
    documents = retrieve_documents(str(user_query))

    # Format retrieved documents for the LLM
    context = "\n\n".join(
        [f"Source {i + 1}: {doc[0].page_content}" for i, doc in enumerate(documents)]
    )
    messages_with_system = (
        [{"type": "system", "content": system_message}]
        + state["messages"]
        + [HumanMessage(content=f"context: {context}")]
    )

    try:
        print(messages_with_system)
        response = llm.invoke(messages_with_system, config)
        return {"messages": response}
    except Exception as e:
        logger.error("Error calling the language model: %s", e)
        raise


# Define the workflow
workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("retrieval", retrieve_documents)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

chain = workflow.compile().with_config({"tags": ["include"]})
