from langgraph.graph import MessagesState, StateGraph
from utils.models import LLM
from utils.tools import tools
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    filter_messages,
    ToolMessage,
)
from utils.prompts import Q_SUGGESTION_TEMPLATE, RAG_TEMPLATE, SUMMARY_TEMPLATE
from dotenv import load_dotenv
import re

load_dotenv()

NOMBRE_PATTERN = re.compile(r"Nombre del documento:\s*(.+)")
FUENTE_PATTERN = re.compile(r"Fuente:\s*(.+)")


class AgentState(MessagesState):
    """State class for managing conversation and suggested questions.

    Attributes:
        suggested_question (str): Next question suggested by the agent
    """

    suggested_question: str
    used_docs: list[dict]


async def model(state: AgentState):
    """Process messages through LLM with bound tools and manage system prompts.

    Args:
        state (AgentState): Current conversation state containing messages

    Returns:
        dict: Updated messages after LLM processing
    """
    llm_with_tools = LLM.bind_tools(tools)
    messages = state["messages"]
    summary = state.get("summarized_conversation", "")

    system_messages = filter_messages(messages, include_types=[SystemMessage])

    if not system_messages:
        formatted_template = RAG_TEMPLATE.format(
            summary=summary if summary else "No hay resumen previo."
        )
        messages.insert(0, SystemMessage(content=formatted_template))

    response = await llm_with_tools.with_config({"run_name": "agent_answer"}).ainvoke(
        messages
    )

    return {"messages": response}


async def pending_tool_calls(state: AgentState):
    """Check if latest AI message contains tool calls and mark for processing.

    Args:
        state (AgentState): Current conversation state

    Returns:
        str: Next node to process - "tools" or "clean_messages"

    Raises:
        TypeError: If last message is not an AIMessage
    """
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage):
        raise TypeError(f"Expected AIMessage, got {type(last_message)}")
    if last_message.tool_calls:
        last_message.name = "tool_message"
        return "tools"
    return "clean_messages"


async def clean_messages(state: AgentState):
    """Remove tool-related messages from conversation history and extract document metadata.

    Args:
        state (AgentState): Current conversation state

    Returns:
        dict: List of messages to remove
    """
    # Filter out tool-related messages
    tool_messages = filter_messages(
        state["messages"],
        include_names=["tool_message"],
        include_types=[ToolMessage],
    )

    used_docs = []
    for msg in tool_messages:
        nombre_match = NOMBRE_PATTERN.search(msg.content)
        fuente_match = FUENTE_PATTERN.search(msg.content)

        if nombre_match and fuente_match:
            used_docs.append(
                {
                    "Nombre del documento": nombre_match.group(1),
                    "Fuente": fuente_match.group(1),
                }
            )

    messages_to_remove = [
        RemoveMessage(id=msg.id) for msg in tool_messages if msg.id is not None
    ]

    return {"messages": messages_to_remove, "used_docs": used_docs}


async def suggest_question(state: AgentState) -> AgentState:
    """Generate follow-up question based on last conversation exchange.

    Args:
        state (AgentState): Current conversation state

    Returns:
        dict: Generated follow-up question
    """
    relevant_messages = state["messages"][-2:]

    formatted_prompt = Q_SUGGESTION_TEMPLATE.format(
        user_input=relevant_messages[0].content,
        bot_response=relevant_messages[1].content,
    )

    response = await LLM.with_config({"run_name": "q_suggestion"}).ainvoke(
        formatted_prompt
    )
    response.name = "suggested_question"
    return {"suggested_question": response.content}


async def check_message_count(state: AgentState):
    """Determine next node based on conversation length.

    Args:
        state (AgentState): Current conversation state

    Returns:
        str: Next node - "suggest_question" or "summarize_conversation"
    """
    messages = filter_messages(
        state["messages"],
        include_types=[HumanMessage, AIMessage],
    )

    if len(messages) < 6:
        return "suggest_question"

    return "summarize_conversation"


async def summarize_conversation(state: AgentState):
    """Generate conversation summary and update system message.

    Args:
        state (AgentState): Current conversation state

    Returns:
        dict: Messages to remove after summarization
    """
    system_message = filter_messages(state["messages"], include_types=[SystemMessage])[
        0
    ]

    messages_to_summarize = filter_messages(
        state["messages"],
        exclude_types=[SystemMessage],
    )

    formatted_conversation = "\n\n".join(
        f"{'USUARIO' if isinstance(msg, HumanMessage) else 'BOT'}: {msg.content}"
        for msg in messages_to_summarize
    )

    formatted_prompt = SUMMARY_TEMPLATE.format(conversation=formatted_conversation)
    response = await LLM.ainvoke(formatted_prompt)

    formatted_template = RAG_TEMPLATE.format(summary=response.content)
    system_message.content = formatted_template

    messages_to_remove = [
        RemoveMessage(id=msg.id) for msg in messages_to_summarize if msg.id is not None
    ]

    return {"messages": messages_to_remove}


async def join_nodes(state: AgentState):
    """Pass through node for graph completion.

    Args:
        state (AgentState): Current conversation state

    Returns:
        AgentState: Unmodified state
    """
    return state


agent_builder = StateGraph(AgentState)
agent_builder.add_node(model)
agent_builder.add_node("tools", ToolNode(tools=tools))
agent_builder.add_node(clean_messages)
agent_builder.add_node(suggest_question)
agent_builder.add_node(summarize_conversation)
agent_builder.add_node(join_nodes)

agent_builder.set_entry_point("model")

agent_builder.add_conditional_edges(
    "model",
    pending_tool_calls,
    {"tools": "tools", "clean_messages": "clean_messages"},
)

agent_builder.add_conditional_edges(
    "clean_messages",
    check_message_count,
    {
        "summarize_conversation": "summarize_conversation",
        "suggest_question": "suggest_question",
    },
)


agent_builder.add_edge("tools", "model")
agent_builder.add_edge("suggest_question", "join_nodes")
agent_builder.add_edge("summarize_conversation", "join_nodes")
agent_builder.set_finish_point("join_nodes")

agent_graph = agent_builder.compile(checkpointer=MemorySaver()).with_config(
    {"run_name": "Agente AquaChile"}
)