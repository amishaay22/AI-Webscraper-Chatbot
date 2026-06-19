from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.chatbot import ask_chatbot

router = APIRouter(prefix="/chat", tags=["chatbot"])


class ChatRequest(BaseModel):
    query: str
    language: str = "en"


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []


@router.post("/ask", response_model=ChatResponse)
async def ask(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        result = ask_chatbot(req.query, language=req.language)
        return ChatResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")
