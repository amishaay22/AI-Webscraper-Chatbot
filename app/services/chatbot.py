from langchain_groq import ChatGroq
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from app.services.ingestion import get_vectorstore

SYSTEM_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant that answers questions based on the provided website content.
Use ONLY the context below to answer. If the answer is not found in the context, say "I don't have enough information about that from the scraped content."

Context:
{context}"""),
("human", "{input}")
])


def ask_chatbot(query: str, language: str = "en") -> dict:
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4},
    )

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        max_tokens=1000,
    )

    qa_chain = create_stuff_documents_chain(llm=llm, prompt=SYSTEM_PROMPT)
    chain = create_retrieval_chain(retriever=retriever, combine_docs_chain=qa_chain)

    if language and language != "en":
        query = f"(Please respond in {language}.) {query}"

    result = chain.invoke({"input": query})

    sources = list({
        doc.metadata.get("source", "")
        for doc in result.get("context", [])
        if doc.metadata.get("source")
    })

    return {
        "answer": result.get("answer", "No answer found."),
        "sources": sources,
    }


def get_chat_history_context(history: list[dict], query: str) -> str:
    """Format recent chat history for context."""
    lines = []
    for msg in history[-6:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        lines.append(f"{role.capitalize()}: {content}")
    lines.append(f"User: {query}")
    return "\n".join(lines)
