import os
import subprocess
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl

from app.cache import is_url_ingested, save_ingested_url, get_all_ingested_urls, remove_ingested_url
from app.services.ingestion import ingest_markdown

router = APIRouter(prefix="/scrape", tags=["scraping"])

# Track running jobs in memory
_jobs: dict[str, dict] = {}


class ScrapeRequest(BaseModel):
    urls: list[str]
    force: bool = False  # re-scrape even if cached


class ScrapeStatus(BaseModel):
    url: str
    status: str
    message: str = ""


def _run_scrape_and_ingest(urls: list[str], job_id: str):
    _jobs[job_id] = {"status": "running", "urls": urls, "completed": [], "failed": []}

    # Join URLs for Scrapy
    urls_str = ",".join(urls)

    try:
        result = subprocess.run(
            ["scrapy", "crawl", "url_scraper", "-a", f"urls={urls_str}"],
            cwd=os.path.join(os.path.dirname(__file__), "../../scraping"),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = result.stderr[-2000:]
            return

    except subprocess.TimeoutExpired:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = "Scraping timed out after 5 minutes."
        return
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(e)
        return

    # Ingest markdown into vector DB
    try:
        ingest_result = ingest_markdown("KnowledgeBase.md")
        _jobs[job_id]["ingest_result"] = ingest_result
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = f"Ingestion failed: {str(e)}"
        return

    # Save to cache
    for url in urls:
        save_ingested_url(url, {"job_id": job_id})

    _jobs[job_id]["status"] = "done"
    _jobs[job_id]["completed"] = urls


@router.post("/start")
async def start_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    new_urls = []
    cached_urls = []

    for url in req.urls:
        if is_url_ingested(url) and not req.force:
            cached_urls.append(url)
        else:
            new_urls.append(url)

    if not new_urls:
        return {
            "message": "All URLs already ingested. Use force=true to re-scrape.",
            "cached": cached_urls,
            "job_id": None,
        }

    import uuid
    job_id = str(uuid.uuid4())[:8]
    background_tasks.add_task(_run_scrape_and_ingest, new_urls, job_id)

    return {
        "message": f"Scraping started for {len(new_urls)} URL(s).",
        "job_id": job_id,
        "new_urls": new_urls,
        "cached_urls": cached_urls,
    }


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("/jobs")
async def list_jobs():
    return _jobs


@router.get("/ingested")
async def list_ingested():
    return get_all_ingested_urls()


@router.delete("/ingested/{url:path}")
async def delete_ingested(url: str):
    remove_ingested_url(url)
    return {"message": f"Removed {url} from cache."}
