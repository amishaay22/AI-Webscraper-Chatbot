from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import scrape, chat, knowledge
from dotenv import load_dotenv
load_dotenv()
app = FastAPI(
    title="WebBot API",
    description="Scrape websites, build a knowledge base, and chat with your data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(scrape.router)
app.include_router(chat.router)
app.include_router(knowledge.router)


@app.get("/")
async def root():
    return {
        "message": "WebBot API is running.",
        "docs": "/docs",
        "endpoints": {
            "scrape": "/scrape/start",
            "chat": "/chat/ask",
            "summary": "/knowledge/summary",
            "faqs": "/knowledge/faqs",
            "export": "/knowledge/export/markdown",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
