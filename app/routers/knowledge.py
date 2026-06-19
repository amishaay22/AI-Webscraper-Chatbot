import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from app.services.ingestion import (
    summarize_knowledge_base,
    generate_faqs,
    export_summary_markdown,
    get_knowledge_base_text,
    ingest_markdown,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/summary")
async def get_summary():
    try:
        summary = await asyncio.to_thread(summarize_knowledge_base)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/faqs")
async def get_faqs():
    try:
        faqs = await generate_faqs()
        return {"faqs": faqs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/markdown", response_class=PlainTextResponse)
async def export_markdown():
    try:
        # md = await asyncio.to_thread(export_summary_markdown)
        md = await export_summary_markdown()
        return md
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/raw")
async def get_raw():
    text = get_knowledge_base_text()
    if not text:
        raise HTTPException(status_code=404, detail="No knowledge base found.")
    return {"content": text[:5000], "total_chars": len(text)}


@router.post("/reingest")
async def reingest():
    try:
        result = await asyncio.to_thread(ingest_markdown, "KnowledgeBase.md")
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))