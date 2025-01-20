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

import json
import logging
import os
from typing import Literal, Union

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

logger = logging.getLogger("invoice_agent")

# Initalize model information
MODEL_GATEWAY_BASE_URL = os.getenv("MODEL_GATEWAY_BASE_URL", None)
MODEL_GATEWAY_MODEL_ID = os.getenv("MODEL_GATEWAY_MODEL_ID", None)

if MODEL_GATEWAY_MODEL_ID is None:
    logger.error("MODEL_GATEWAY_MODEL_ID is not set")
    raise Exception("MODEL_GATEWAY_MODEL_ID is not set")


class Invoice(TypedDict):
    supplier: str
    amount: int
    date: str
    status: str


database = {
    "invoice_001": Invoice(
        supplier="ABC Corp", amount=1500, date="2023-10-01", status="Paid"
    ),
    "invoice_002": Invoice(
        supplier="XYZ Ltd", amount=2500, date="2023-10-05", status="Pending"
    ),
}


@tool
def fetch_invoice_info(invoice_id: str) -> Union[Invoice, Literal["Invoice not found"]]:
    """Fetch invoice information from the database."""
    record = database.get(invoice_id)
    if record is None:
        return "Invoice not found"
    logger.info(
        f"Fetching invoice info for invoice {invoice_id}: {json.dumps(record, indent=2)}"
    )
    return record


@tool
def change_invoice_status(invoice_id: str, new_status: str) -> str:
    """Change the status of an invoice in the database."""
    logger.info(f"Changing status of invoice {invoice_id} to {new_status}.")
    logger.info(f"""Old record: {json.dumps(database[invoice_id], indent=2)}\n
New record: {json.dumps(database[invoice_id], indent=2)}""")
    database[invoice_id]["status"] = new_status
    return f"Invoice status changed to {new_status}"


@tool
def create_new_invoice(new_invoice: Invoice, invoice_id: str) -> str:
    """Create a new invoice in the database."""
    database[invoice_id] = Invoice(**new_invoice)
    logger.info(f"New invoice created: {json.dumps(database[invoice_id], indent=2)}")
    return f"Invoice {invoice_id} created successfully"


tools = [fetch_invoice_info, change_invoice_status, create_new_invoice]

llm = ChatOpenAI(
    model=MODEL_GATEWAY_MODEL_ID,
    base_url=MODEL_GATEWAY_BASE_URL,
    temperature=0,
    streaming=True,
).bind_tools(tools)


def should_continue(state: MessagesState) -> str:
    """Determines whether to use tools or end the conversation."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


def call_model(state: MessagesState, config: RunnableConfig) -> dict[str, BaseMessage]:
    """Calls the language model and returns the response."""
    system_message = """
You are provided with a tool to perform a database lookup when the user requests the status
of an invoice with an invoice id. Perform the lookup and provide the status to the user in a
clear, readable format. The status should be every field in the entry returned from the database on a separate line."""
    messages_with_system = [{"type": "system", "content": system_message}] + state[
        "messages"
    ]
    # Forward the RunnableConfig object to ensure the agent is capable of streaming the response.
    response = llm.invoke(messages_with_system, config)
    return {"messages": response}


workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))
workflow.set_entry_point("agent")

workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

chain = workflow.compile().with_config({"tags": ["include"]})
