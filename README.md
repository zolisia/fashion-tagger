# Fashion Tagger

Paste a product URL, get back five structured fashion attributes.

The app pulls the main product image from the page's `og:image` meta tag, sends it to Claude's vision API with a JSON-schema constraint, and renders the tags next to the image.

## Screenshot

![Tagger screenshot](Tagger.png)

_Hobbs petite Cathy jersey dress, correctly tagged as: dress · V-neck · short sleeve · A-line · smart-casual._

## Attributes extracted

| Attribute       | Possible values                                                            |
| --------------- | -------------------------------------------------------------------------- |
| `garment_type`  | dress, top, trousers, skirt, jacket, knitwear, other                       |
| `neckline`      | crew, V, scoop, square, halter, off-shoulder, N/A                          |
| `sleeve_type`   | sleeveless, short, long, 3/4, cap, puff, N/A                               |
| `silhouette`    | fitted, A-line, oversized, straight, flared, cropped                       |
| `formality`     | casual, smart-casual, formal, occasion                                     |

The five values are returned as a JSON object validated against a JSON schema, so you'll always get exactly these keys with values from the allowed enums.

## Tech stack

- **Backend** — Python 3.10+, [FastAPI](https://fastapi.tiangolo.com/), uvicorn
- **Vision model** — [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python), Claude Opus 4.7 with structured JSON output
- **Scraping** — `requests` + `beautifulsoup4` for `og:image` extraction (with `twitter:image` fallback)
- **Frontend** — vanilla HTML / CSS / JavaScript, no build step, no framework
- **Config** — `python-dotenv`

## Run locally

You'll need Python 3.10+ and an Anthropic API key from [console.anthropic.com](https://console.anthropic.com/).

```bash
git clone https://github.com/zolisia/fashion-tagger.git
cd fashion-tagger

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# open .env and paste your ANTHROPIC_API_KEY

uvicorn main:app --reload --port 8000
```

Then open http://localhost:8000 and paste a product URL.

## How it works

1. Frontend POSTs `{url}` to `/api/tag`.
2. Backend fetches the page HTML, finds `<meta property="og:image">` (falling back to `og:image:secure_url` and `twitter:image`), and resolves any relative URL against the page URL.
3. Backend downloads the image bytes and base64-encodes them.
4. Claude `claude-opus-4-7` is called with the image plus a JSON-schema constraint that enforces the five attributes and their enums.
5. Frontend renders the image and tags side-by-side.

A request takes 3–5 seconds end-to-end depending on image size.

## Known limitations

**Bot-protected retailers.** Many large fashion sites (Net-a-Porter, Zara, Farfetch, ASOS, COS, SSENSE) detect non-browser HTTP clients. v2 added a Playwright headless-browser fallback that fires automatically when the fast `requests` path fails — but default Playwright is also detected by the most aggressive defenses (Datadome, Cloudflare bot management). The fallback architecture is correct (fast path → graceful degradation → clean error), but defeating these defenses requires further work: stealth plugins, residential proxies, or a paid scraping API. See `notes/evaluation-week1.md` for tested results. Ship-quality scraping is a v3 concern; the current build handles smaller and indie retailers well.

**Pages with no `og:image`.** Most retailers include one, but if they don't, the app returns a friendly 422 error and asks for a different link.

**Single-garment images only.** The model is prompted to tag the main garment in the photo. Flat-lays with multiple items, or full outfits on a model with several pieces, will be tagged based on whichever garment the model considers primary.

**Cost.** Each tag call is one Claude Opus 4.7 vision request — roughly $0.005–0.01 per request at typical image sizes. To cut costs ~5×, swap to `claude-haiku-4-5` in `main.py`.

**No persistence.** No database, no history, no accounts. By design — this is the simplest version that works.

## Project structure

```
fashion-tagger/
├── main.py              # FastAPI app: og:image extraction + Claude vision call
├── requirements.txt
├── .env.example         # template — copy to .env and add your key
├── .gitignore           # .env and venv excluded
├── static/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── Tagger.png           # screenshot used in this README
└── README.md
```

## Proof of concept

Using a full fledged LLM for fashion classification is overkill for this repo. This script is intentionally a proof of concept and it consumes more resources than an optimized production system would. In a production version, the goal would be to use a solution tuned specifically for this task.

I am confident that repositories like HuggingFace already offer models that can work well with fashion data. Another development path would be to use a mini version of an LLM or fine-tune a model on a dataset tailored to this domain. I already have a highly reliable dataset from photos of my own clothes, which would make fine-tuning especially effective.

## Future direction

The current implementation calls Claude Opus 4.7 for every image — convenient for a v1, but overkill for a 5-attribute classification task in production. Future versions will explore lighter-weight approaches:

- **Fashion-specific models from HuggingFace** (e.g. FashionCLIP, fashion-tuned CNNs) as drop-in replacements for the foundation model. Trade-off: lower per-call cost and ~50ms latency vs. ~3–5 seconds, at the cost of more setup and a narrower domain.
- **Fine-tuning a smaller model** (Claude Haiku, or an open-source vision model) on a labeled fashion dataset. Personal wardrobe photos from a separate cataloguing project provide a starting dataset; this would need expansion to 500+ properly-labeled images for meaningful fine-tuning.
- **Target metrics for v3:** <100ms latency, <$0.001 per call, comparable accuracy to current Opus 4.7 baseline (~90% on tested attributes).

Why this matters: at consumer-app scale (e.g. tagging every product on a category page in real time), per-call cost dominates. The current architecture is the right *first* version; production economics demand a different one.

*Credit: feedback from a senior engineer (May 2026) — exactly the right pushback for a v1 to receive.*

## Roadmap

- [ ] Playwright fallback for bot-protected retailers
- [ ] Expanded taxonomy (color, fabric, pattern)
- [ ] Batch tagging from CSV of URLs
- [ ] Optional persistence layer for tagged history
- [ ] v3: Investigate HuggingFace fashion models / fine-tuning for cost & speed optimization

---

Built by zolisia · April 2026
