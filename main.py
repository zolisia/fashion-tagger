import json
import os
from pathlib import Path
from urllib.parse import urljoin

import requests
from anthropic import Anthropic, APIError
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

client = Anthropic()

TAG_SCHEMA = {
    "type": "object",
    "properties": {
        "garment_type": {
            "type": "string",
            "enum": ["dress", "top", "trousers", "skirt", "jacket", "knitwear", "other"],
        },
        "neckline": {
            "type": "string",
            "enum": ["crew", "V", "scoop", "square", "halter", "off-shoulder", "N/A"],
        },
        "sleeve_type": {
            "type": "string",
            "enum": ["sleeveless", "short", "long", "3/4", "cap", "puff", "N/A"],
        },
        "silhouette": {
            "type": "string",
            "enum": ["fitted", "A-line", "oversized", "straight", "flared", "cropped"],
        },
        "formality": {
            "type": "string",
            "enum": ["casual", "smart-casual", "formal", "occasion"],
        },
    },
    "required": ["garment_type", "neckline", "sleeve_type", "silhouette", "formality"],
    "additionalProperties": False,
}

PROMPT = (
    "Tag this fashion product image. Look at the single main garment shown. "
    "If an attribute does not apply (e.g. neckline on trousers, sleeves on a skirt), "
    "use N/A where allowed, otherwise pick the closest enum value. "
    "Return only the structured JSON."
)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class TagRequest(BaseModel):
    url: HttpUrl


class TagResponse(BaseModel):
    image_url: str
    tags: dict


app = FastAPI(title="Tagger")


def extract_og_image(page_url: str) -> str:
    try:
        r = requests.get(page_url, headers=BROWSER_HEADERS, timeout=12, allow_redirects=True)
        r.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Couldn't load that page ({e.__class__.__name__}). Double-check the link.")

    soup = BeautifulSoup(r.text, "html.parser")
    candidates = [
        ("meta", {"property": "og:image"}),
        ("meta", {"name": "og:image"}),
        ("meta", {"property": "og:image:secure_url"}),
        ("meta", {"name": "twitter:image"}),
    ]
    for tag, attrs in candidates:
        el = soup.find(tag, attrs=attrs)
        if el and el.get("content"):
            return urljoin(str(r.url), el["content"].strip())

    raise HTTPException(
        status_code=422,
        detail="No og:image meta tag on this page. Try a different product link — most retailers include one.",
    )


def fetch_image_bytes(image_url: str) -> tuple[bytes, str]:
    try:
        r = requests.get(image_url, headers=BROWSER_HEADERS, timeout=15, allow_redirects=True)
        r.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Found an image link but couldn't download it ({e.__class__.__name__}).")

    media_type = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if media_type not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
        if image_url.lower().endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif image_url.lower().endswith(".png"):
            media_type = "image/png"
        elif image_url.lower().endswith(".webp"):
            media_type = "image/webp"
        elif image_url.lower().endswith(".gif"):
            media_type = "image/gif"
        else:
            media_type = "image/jpeg"

    return r.content, media_type


def tag_image(image_bytes: bytes, media_type: str) -> dict:
    import base64

    data = base64.standard_b64encode(image_bytes).decode("ascii")

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        output_config={"format": {"type": "json_schema", "schema": TAG_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": data},
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )

    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise HTTPException(status_code=502, detail="Model returned no text content.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Model returned invalid JSON.")


@app.post("/api/tag", response_model=TagResponse)
def tag(req: TagRequest):
    image_url = extract_og_image(str(req.url))
    image_bytes, media_type = fetch_image_bytes(image_url)
    try:
        tags = tag_image(image_bytes, media_type)
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {e.message if hasattr(e, 'message') else str(e)}")
    return TagResponse(image_url=image_url, tags=tags)


STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
