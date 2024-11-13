from langchain.tools.retriever import create_retriever_tool
from utils.models import PINECONE_VECTOR_STORE
from langchain_core.prompts import PromptTemplate

document_prompt = PromptTemplate.from_template(
    "Nombre del documento: {filename} \nFuente: {source}\nContenido: {page_content}"
)

retriever_tool = create_retriever_tool(
    PINECONE_VECTOR_STORE.as_retriever(),
    name="aquachile-retriever",
    description="search and retrieve information from AquaChile's knowledge base",
    document_prompt=document_prompt,
)

tools = [retriever_tool]
