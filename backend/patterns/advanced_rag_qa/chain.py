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
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger("advanced_rag_qa")

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

system_prompt = SystemMessage(
    content="You are a helpful assistant that answers questions about the Tennessee State Legislature."
)


@tool
def retrieve_documents(query: str) -> tuple[str, list[Document]]:
    """Retrieve relevant documents based on the query."""
    try:
        results = vector_store.similarity_search(query, k=5)
        logger.info("Retrieved documents: %s", results)
        if not results:
            logger.warning("No documents retrieved for query: %s", query)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata}\nContent: {doc.page_content}") for doc in results
        )
        return serialized, results
    except Exception as e:
        logger.error("Error retrieving documents: %s", e)
        raise


def query_or_respond(state: MessagesState) -> dict[str, list[BaseMessage]]:
    """Generate tool call for retrieval or respond."""

    messages = [system_prompt] + state["messages"]
    llm_with_tools = llm.bind_tools([retrieve_documents])
    response = llm_with_tools.invoke(messages)
    # MessagesState appends messages to state instead of overwriting
    return {"messages": [response]}


tools = ToolNode([retrieve_documents])


def call_model(
    state: MessagesState, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    """Calls the language model and returns the response."""

    recent_tool_messages = []
    for message in reversed(state["messages"]):
        if message.type == "tool":
            recent_tool_messages.append(message)
        else:
            break
    tool_messages = recent_tool_messages[::-1]

    docs_content = "\n\n".join(str(doc.content) for doc in tool_messages)

    messages = (
        [system_prompt] + state["messages"] + [HumanMessage(f"context: {docs_content}")]
    )

    try:
        response = llm.invoke(messages, config)
        return {"messages": [response]}
    except Exception as e:
        logger.error("Error calling the language model: %s", e)
        raise


# Define the workflow
graph_builder = StateGraph(MessagesState)
graph_builder.add_node(query_or_respond)
graph_builder.add_node(tools)
graph_builder.add_node(call_model)

graph_builder.set_entry_point("query_or_respond")
graph_builder.add_conditional_edges(
    "query_or_respond",
    tools_condition,
    {END: END, "tools": "tools"},
)
graph_builder.add_edge("tools", "call_model")
graph_builder.add_edge("call_model", END)

chain = graph_builder.compile().with_config({"tags": ["include"]})
