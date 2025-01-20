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
from typing import Annotated, Literal, Sequence, TypedDict

from langchain.tools.retriever import create_retriever_tool
from langchain_community.tools import TavilySearchResults
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger("agentic_rag")

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

retriever = vector_store.as_retriever()

retriever_tool = create_retriever_tool(
    retriever,
    name="retrieve_tennessee_documents",
    description="Search and return information about Tennessee. This tool does not return information about other States.",
)

tools = [retriever_tool]

tavily_search_tool = TavilySearchResults(
    description="Only use this search tool when other tools cannot provide the answer."
)

tools.append(tavily_search_tool)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def grade_documents(state) -> Literal["generate", "rewrite"]:
    print("---CHECK RELEVANCE---")

    class grade(BaseModel):
        binary_score: str = Field(description="Relevance score 'yes' or 'no'")

    llm = ChatOpenAI(temperature=0, streaming=True, model="gpt-4o-mini")
    llm_with_tool = llm.with_structured_output(grade)

    messages = state["messages"]
    last_message = messages[-1]

    question = messages[0].content
    docs = last_message.content

    input_message_text = (
        "You are a grader assessing relevance of retrieved documents to a user question. "
        f"context: {docs}"
        f"question: {question}"
        "If the documents contain keywords or semantic meaning related to the user question, grade them as relevant. "
        "Give a binary score of a 'yes' or 'no' to indicate whether the document is relevant to the question."
    )

    messages = [HumanMessage(content=input_message_text)]

    scored_result = llm_with_tool.invoke(messages)

    score = scored_result.binary_score

    if score == "yes":
        print("---DECISION: DOCS RELEVANT---")
        print(score)
        return "generate"
    else:
        print("---DECISION: DOCS NOT RELEVANT---")
        print(score)
        return "rewrite"


def agent(state):
    print("---CALL AGENT---")
    messages = state["messages"]
    llm = ChatOpenAI(temperature=0, streaming=True, model="gpt-4o-mini")
    llm_with_tools = llm.bind_tools(tools).with_config({"tags": ["include"]})
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def rewrite(state):
    print("---TRANSFORM QUERY---")
    messages = state["messages"]
    question = messages[0].content

    message = [
        HumanMessage(
            content=f""" \n
    Look at the input and try to reason about the underlying semantic intent/meaning. \n
    Here is the initial question:
    \n ------ \n
    {question}
    \n ------ \n
    Formulate an improved question: """,
        )
    ]

    llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", streaming=True)
    response = llm.invoke(message)
    return {"messages": [response]}


def generate(state):
    print("---GENERATE---")
    messages = state["messages"]
    question = messages[0].content
    last_message = messages[-1]

    docs = last_message.content

    system_prompt_message = (
        "You are an assistant for question & answering tasks. "
        "Use the following pieces of retrieved context to answer the question. "
        "If you don't know the answer, then politely say that you do not know the answer. "
        "Use a maximum of three sentences and keep answers concise. "
    )

    system_message = SystemMessage(content=system_prompt_message)

    llm = ChatOpenAI(
        model_name="gpt-4o-mini", temperature=0, streaming=True
    ).with_config({"tags": ["include"]})

    messages = [system_message, HumanMessage(f"question: {question}\ncontext: {docs}")]

    response = llm.invoke(messages).content

    return {"messages": [response]}


workflow = StateGraph(AgentState)

# Add nodes to our graph
workflow.add_node("agent", agent)
tool_node = ToolNode(tools).with_config({"tags": ["include"]})
workflow.add_node("tools", tool_node)
workflow.add_node("rewrite", rewrite)
workflow.add_node("generate", generate)

# We start with agent
workflow.add_edge(START, "agent")

# This is where we determine if we a made a tool call
workflow.add_conditional_edges(
    "agent",
    # Did the agent call or a tool or not?
    tools_condition,
    {
        # If we did call a tool, then use the tool
        # If not, then we generate
        "tools": "tools",
        END: END,
    },
)

# If we retrieved documents, then we grade them.
# grade_documents determines where we go next based on the score: generate or rewrite
workflow.add_conditional_edges(
    "tools",
    grade_documents,
)

# If we called a tool, then we call generate.
workflow.add_edge("generate", END)
# If we need to rewrite, then we call the agent again
workflow.add_edge("rewrite", "agent")

# Compile our workflow
chain = workflow.compile()
