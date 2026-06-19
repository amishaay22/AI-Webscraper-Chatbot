import os
import re
import json

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

CHROMA_DIR = "chroma_db"
KNOWLEDGE_BASE = "KnowledgeBase.md"
COLLECTION_NAME = "knowledge"


# ─────────────────────────────────────────────────────────────
# Embeddings + Vector Store
# ─────────────────────────────────────────────────────────────

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )


def get_vectorstore():
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )


# ─────────────────────────────────────────────────────────────
# Markdown Cleaning
# ─────────────────────────────────────────────────────────────

def clean_markdown(text: str) -> str:
    """Remove markdown formatting for cleaner embeddings."""

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Remove markdown headings
    text = re.sub(r"#+\s+", "", text)

    # Remove bold / italic
    text = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.*?)_{1,3}", r"\1", text)

    # Remove markdown links
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)

    # Remove images
    text = re.sub(r"!\[[^\]]*\]\([^\)]+\)", "", text)

    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Remove code blocks
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)

    # Remove blockquotes
    text = re.sub(r"^\s*>\s+", "", text, flags=re.MULTILINE)

    # Remove bullet points
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

    # Remove table formatting
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"[-:]+", " ", text)

    # Clean extra spaces/newlines
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ─────────────────────────────────────────────────────────────
# Ingestion
# ─────────────────────────────────────────────────────────────

def ingest_markdown(filepath: str = KNOWLEDGE_BASE) -> str:

    if not os.path.exists(filepath):
        return f"Error: {filepath} not found."

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        return "Error: KnowledgeBase.md is empty."

    # Clean markdown
    text = clean_markdown(text)

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=80,
    )

    chunks = splitter.split_text(text)

    if not chunks:
        return "No content to ingest."

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )

    # Batch insertion
    BATCH_SIZE = 200

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        vectorstore.add_texts(batch)

    return f"Ingested {len(chunks)} chunks into vector store."


# ─────────────────────────────────────────────────────────────
# Summary Generation
# ─────────────────────────────────────────────────────────────

def summarize_knowledge_base() -> str:
    """Generate concise summary from knowledge base."""

    if not os.path.exists(KNOWLEDGE_BASE):
        return "No knowledge base found."

    with open(KNOWLEDGE_BASE, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        return "Knowledge base is empty."

    trimmed = text[:12000]

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        max_tokens=1000,
    )

    response = llm.invoke(
        f"""
        Summarize the following scraped website content.

        Rules:
        - Use 5-8 concise bullet points
        - Keep it professional and readable
        - Highlight key topics and insights
        - Avoid repeating information

        Content:
        {trimmed}
        """
    )

    return response.content


# ─────────────────────────────────────────────────────────────
# FAQ Generation
# ─────────────────────────────────────────────────────────────

async def generate_faqs() -> list[dict]:
    """Generate FAQs from knowledge base."""

    if not os.path.exists(KNOWLEDGE_BASE):
        return []

    with open(KNOWLEDGE_BASE, "r", encoding="utf-8") as f:
        text = f.read()

    if not text.strip():
        return []

    trimmed = text[:10000]

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        max_tokens=1500,
    )

    prompt = f"""
    Based on the following scraped website content,
    generate 6 professional FAQs and answers.

    IMPORTANT:
    - Return ONLY valid JSON
    - No markdown
    - No explanations
    - Format must be:

    [
      {{
        "question": "...",
        "answer": "..."
      }}
    ]

    Content:
    {trimmed}
    """

    response = llm.invoke(prompt)

    raw = response.content

    # Remove markdown fences if model adds them
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        faqs = json.loads(raw)

        if isinstance(faqs, list):
            return faqs

        return []

    except Exception as e:
        print("FAQ JSON PARSE ERROR:", e)
        print("RAW RESPONSE:", raw)

        return []


# ─────────────────────────────────────────────────────────────
# Export Markdown
# ─────────────────────────────────────────────────────────────

async def export_summary_markdown() -> str:
    """Export summary + FAQs as markdown."""

    summary = summarize_knowledge_base()

    faqs = await generate_faqs()

    md = "# Knowledge Base Summary\n\n"

    md += f"{summary}\n\n"

    md += "---\n\n"

    md += "## Frequently Asked Questions\n\n"

    for faq in faqs:
        md += f"### Q: {faq.get('question', '')}\n\n"
        md += f"{faq.get('answer', '')}\n\n"

    return md


# ─────────────────────────────────────────────────────────────
# Raw Knowledge Base
# ─────────────────────────────────────────────────────────────

def get_knowledge_base_text() -> str:

    if not os.path.exists(KNOWLEDGE_BASE):
        return ""

    with open(KNOWLEDGE_BASE, "r", encoding="utf-8") as f:
        return f.read()