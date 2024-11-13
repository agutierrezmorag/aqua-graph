from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv

load_dotenv()

LLM = ChatOpenAI(model="gpt-4o-mini", max_tokens=1000, temperature=0.7)

EMBEDDINGS_MODEL = OpenAIEmbeddings(model="text-embedding-3-small")

CHROMA_VECTOR_STORE = Chroma(
    collection_name="aquachile_collection",
    embedding_function=EMBEDDINGS_MODEL,
    persist_directory="./chroma_langchain_db",
)

PINECONE_VECTOR_STORE = PineconeVectorStore(
    index_name="chainlit-ai-app",
    embedding=EMBEDDINGS_MODEL,
)
