import collections
import datetime
import logging
import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from answer import answer

logger = logging.getLogger("api")

app = FastAPI(title="AI Earnings Analyst")

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# Abuse protection (all configurable through environment variables)
RATE_WINDOW_SECONDS = int(os.getenv("RATE_WINDOW_SECONDS", "600"))
RATE_MAX_PER_WINDOW = int(os.getenv("RATE_MAX_PER_WINDOW", "10"))
DAILY_MAX = int(os.getenv("DAILY_MAX", "300"))

_lock = threading.Lock()
_recent = collections.defaultdict(collections.deque)  # ip -> timestamps of recent requests
_daily = {"date": None, "count": 0}


def client_ip(request: Request):
    """The caller's IP. Behind a proxy the last X-Forwarded-For entry is the one the proxy added."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def check_limits(ip):
    """Raise HTTP 429 if this caller or the whole service is over its limit; otherwise count the request."""
    now = time.time()
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    with _lock:
        if _daily["date"] != today:
            _daily["date"], _daily["count"] = today, 0
        if _daily["count"] >= DAILY_MAX:
            raise HTTPException(
                status_code=429,
                detail="The demo has reached its daily limit. Please try again tomorrow.",
            )

        window = _recent[ip]
        while window and now - window[0] > RATE_WINDOW_SECONDS:
            window.popleft()
        if len(window) >= RATE_MAX_PER_WINDOW:
            retry_after = int(RATE_WINDOW_SECONDS - (now - window[0])) + 1
            raise HTTPException(
                status_code=429,
                detail="Too many questions. Please wait a few minutes and try again.",
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)
        _daily["count"] += 1

        if len(_recent) > 1000:  # forget callers with no recent requests
            for key in [k for k, v in _recent.items() if not v or now - v[-1] > RATE_WINDOW_SECONDS]:
                del _recent[key]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    k: int = Field(default=5, ge=1, le=10)


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(body: AskRequest, request: Request):
    check_limits(client_ip(request))
    start = time.time()
    try:
        result, hits = answer(body.question.strip(), k=body.k)
    except Exception:
        logger.exception("answer() failed")
        raise HTTPException(status_code=502, detail="Answer generation failed. Please try again.")

    return {
        "answer": result["text"],
        "sources": [
            {
                "n": i,
                "ticker": h["ticker"],
                "doc_type": h["doc_type"],
                "date": h["date"],
                "source": h["source"],
                "score": round(h["score"], 3),
                "text": h["text"],
            }
            for i, h in enumerate(hits, start=1)
        ],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "seconds": round(time.time() - start, 2),
    }