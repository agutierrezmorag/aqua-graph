import logging
from typing import Optional

import chainlit as cl
from langchain_core.messages import HumanMessage
from openai import APIError, RateLimitError

from graph import agent_graph


@cl.on_chat_start
async def on_chat_start():
    """
    Initialize chat session with agent and config.

    This function is triggered when a chat session starts. It initializes the session
    by setting various session variables such as the session ID, agent configuration,
    and suggested questions.

    - Retrieves the session ID from the user session.
    - Sets the 'config' variable in the user session with the session ID.
    - Sets the 'agent' variable in the user session with the agent graph.
    - Initializes 'suggested_question' and 'suggested_question_message' to None.
    """

    # Retrieve the session ID from the user session
    session_id = cl.user_session.get("id")

    # Set the 'config' variable in the user session with the session ID
    cl.user_session.set(
        "config",
        {
            "configurable": {"thread_id": session_id},
        },
    )

    # Set the 'agent' variable in the user session with the agent graph
    cl.user_session.set("agent", agent_graph)

    # Initialize 'suggested_question' and 'suggested_question_message' to None
    cl.user_session.set("suggested_question", None)
    cl.user_session.set("suggested_question_message", None)


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming user messages in the chat interface with comprehensive error handling.

    This function processes incoming chat messages, manages conversation state, generates AI responses,
    and handles suggested follow-up questions. It includes error handling for API failures,
    rate limits, and unexpected errors.

    Args:
        message (cl.Message): The incoming chat message object containing user input

    Returns:
        None: Messages are sent directly through the chainlit interface

    Raises:
        ValueError: If agent or config is not properly initialized
        RateLimitError: If OpenAI API rate limits are exceeded
        APIError: If there are issues with the OpenAI API calls
        Exception: For any other unexpected errors
    """
    # Initialize error tracking
    msg: Optional[cl.Message] = None

    try:
        # Clear previous suggested question
        suggested_question_message = cl.user_session.get("suggested_question_message")
        if suggested_question_message:
            await suggested_question_message.remove()
            cl.user_session.set("suggested_question_message", None)
            cl.user_session.set("suggested_question", None)

        agent = cl.user_session.get("agent")
        config = cl.user_session.get("config")

        if not agent or not config:
            raise ValueError("Agent or config not initialized")

        inputs = {"messages": [HumanMessage(content=message.content)]}
        elements = []
        msg = cl.Message(content="")

        async for event in agent.astream_events(
            inputs,
            config,
            version="v2",
        ):
            try:
                event_name = event["name"]
                event_type = event["event"]

                if (
                    event_type == "on_chat_model_stream"
                    and event_name == "agent_answer"
                ):
                    content = event["data"]["chunk"].content
                    if content:
                        await msg.stream_token(content)

                if event_type == "on_chain_end" and event_name == "Agente AquaChile":
                    # Process suggested question
                    q_content = event["data"]["output"].get("suggested_question")
                    if q_content:
                        cl.user_session.set("suggested_question", q_content)

                    # Process documents
                    d_content = event["data"]["output"].get("used_docs", [])
                    elements = [
                        cl.Pdf(
                            name=doc["Nombre del documento"].strip(),
                            display="side",
                            url=doc["Fuente"],
                        )
                        for doc in d_content
                        if doc.get("Nombre del documento") and doc.get("Fuente")
                    ]

            except KeyError as ke:
                logging.error(f"Invalid event structure: {ke}")
                continue
            except Exception as e:
                logging.error(f"Error processing event: {e}")
                continue

        # Send message with elements
        if elements:
            msg.elements = elements
        await msg.send()

        # Handle suggested question
        try:
            suggested_question = cl.user_session.get("suggested_question")
            if suggested_question:
                actions = [
                    cl.Action(
                        name="suggested_question",
                        label=f"{suggested_question}",
                        value=suggested_question,
                        description=suggested_question,
                    )
                ]
                cl.user_session.set(
                    "suggested_question_message",
                    await cl.Message(
                        content="",
                        actions=actions,
                        type="system_message",
                        author="Sugerencia",
                    ).send(),
                )
        except Exception as e:
            logging.error(f"Error setting suggested question: {e}")

    except RateLimitError:
        await cl.Message(
            content="Lo siento, estamos experimentando límites de API. Por favor, intenta nuevamente en unos momentos."
        ).send()

    except APIError as e:
        logging.error(f"API Error: {e}")
        await cl.Message(
            content="Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta nuevamente."
        ).send()

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await cl.Message(
            content="Lo siento, ocurrió un error inesperado. Por favor, intenta nuevamente."
        ).send()


@cl.action_callback("suggested_question")
async def on_action(action: cl.Action):
    """
    Handle suggested question clicks.

    This function is triggered when a suggested question is clicked. It sends a message
    with the content of the action as if it were a user message and then calls the
    `on_message` function to process the suggested question.

    Args:
        action (cl.Action): The action containing the suggested question.
    """

    # Send a message with the content of the action as if it were a user message
    await cl.Message(content=action.value, author="User", type="user_message").send()

    # Call the on_message function to process the suggested question
    await on_message(cl.Message(content=action.value))


@cl.set_starters
async def set_starters():
    """
    Define the initial messages for the chat.

    This function sets up a list of initial messages (`Starters`) that will be displayed
    to the user when a chat session starts. Each initial message includes a label,
    a message, and an associated icon.

    Returns:
        list: A list of `Starter` objects with the information of the initial messages.
    """
    return [
        cl.Starter(
            label="Comité de Integridad",
            message="¿Quiénes conforman el comité de integridad?",
            icon="public/icons/group.png",
        ),
        cl.Starter(
            label="Política de Regalos",
            message="¿Qué hago en caso de recibir un regalo?",
            icon="public/icons/giftbox.png",
        ),
        cl.Starter(
            label="Canal de Denuncias",
            message="¿Cómo puedo hacer una denuncia anónima y qué información debo proporcionar?",
            icon="public/icons/shield.png",
        ),
        cl.Starter(
            label="Conflictos de Interés",
            message="¿Qué situaciones se consideran conflicto de interés y cómo debo reportarlas?",
            icon="public/icons/conflict-of-interest.png",
        ),
    ]
