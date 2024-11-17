from langchain_core.runnables import ConfigurableField
from langchain_openai import ChatOpenAI

LLM = ChatOpenAI(
    model="gpt-4o-mini",
    max_tokens=1000,
    temperature=0.7,
    streaming=True,
).configurable_fields(
    temperature=ConfigurableField(
        id="llm_temperature",
        name="LLM Temperature",
        description="The temperature of the LLM",
    )
)
