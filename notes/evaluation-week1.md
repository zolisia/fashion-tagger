# Tagger Evaluation — Week 1

**Date:** 1 May 2026
**Goal:** Test the tagger on retailer sites, document which work and how accurate the tags are.

---

## Site 1 — COS

- **URL:** cos.com/en-gb/women/womenswear/dresses/linen/product/bias-cut-linen-...
- **Status:** ❌ Failed
- **Error:** HTTPError (likely 403 — bot protection)
- **Tags:** N/A
- **Notes:** COS blocks plain `requests` at the HTTP layer. Different failure mode than ASOS (instant error vs timeout). Confirms the bot-protection limitation.

---

## Site 2 — Etsy

- **URL:** etsy.com/listing/4490109990/handmade-summer-dress-for-women-...
- **Status:** ❌ Failed
- **Error:** HTTPError
- **Tags:** N/A
- **Notes:** Surprising — Etsy was expected to work. May be the specific listing or session-based protection. Worth retesting on a different Etsy listing.

---

## Site 3 — Uniqlo

- **URL:** uniqlo.com/uk/en/products/E483869-000/00 (linen striped shirt)
- **Status:** ✅ Worked
- **Tags:** top / N/A / long / straight / smart-casual
- **Accuracy:** 4/5
- **Notes:** Neckline returned N/A — the shirt has a collar, but the taxonomy doesn't include "collared" as an option. **Taxonomy gap, not a model failure.** Add "collared" or "shirt-collar" to neckline enum in v2.

---

## Site 4 — Vinted

- **URL:** Vinted listing — pink plaid summer dress (size 18)
- **Status:** ✅ Worked
- **Tags:** dress / scoop / sleeveless / A-line / casual
- **Accuracy:** 5/5
- **Notes:** Impressive — handled a non-studio, user-uploaded photo on a hanger against a door. Real-world image quality, perfect tags.

---

## Site 5 — ASOS

- **URL:** asos.com/asos-design/asos-design-crochet-knit-summer-mini-dress-in...
- **Status:** ❌ Failed
- **Error:** ReadTimeout
- **Tags:** N/A
- **Notes:** Confirmed — ASOS blocks plain HTTP requests. Same as Net-a-Porter behaviour. Both will need Playwright fallback.

---

## Site 6 — Ro&Zo (bonus)

- **URL:** roandzo.com/collections/dresses/products/blue-and-white-stripe-cotton-one-...
- **Status:** ✅ Worked
- **Tags:** dress / off-shoulder / sleeveless / A-line / occasion
- **Accuracy:** 4/5
- **Notes:** Garment is actually one-shoulder, not off-shoulder — but "one-shoulder" isn't in the taxonomy enum. Same kind of gap as Uniqlo's neckline. **Add "one-shoulder" to neckline enum in v2.**

---

## Site 7 — Boden (bonus)

- **URL:** boden.com/products/women-tamsin-jersey-midi-dress-fresh-green-an...
- **Status:** ✅ Worked
- **Tags:** dress / crew / sleeveless / A-line / smart-casual
- **Accuracy:** 5/5
- **Notes:** Clean. No issues.

---

## Summary

- **Tested:** 7 sites
- **Worked:** 4/7 (Uniqlo, Vinted, Ro&Zo, Boden)
- **Failed:** 3/7 (COS, Etsy, ASOS)
- **Failure modes:** HTTPError (COS, Etsy) + ReadTimeout (ASOS) — all bot-protection related
- **Average accuracy on successful tags:** 18/20 (90%)
- **Most accurate attribute:** garment_type, sleeve_type, silhouette (5/5 on every working site)
- **Least accurate attribute:** neckline (2 misses, both due to **taxonomy gaps**, not model errors)
- **Surprises:**
  - Vinted (user-uploaded chaotic photos) performed perfectly — the model handles real-world image quality well
  - Etsy failed unexpectedly — worth retesting with a different listing
  - Both neckline misses were the same root cause: missing enum values

## Findings to action in v2

1. **Add Playwright fallback** for bot-protected sites (COS, ASOS, likely Net-a-Porter, Zara, Farfetch)
2. **Expand neckline taxonomy:** add `collared`, `one-shoulder` (and possibly `boat`, `cowl`)
3. **Retest Etsy** — may have been a session-specific issue rather than systemic
4. The vision model itself is performing well; the bottleneck is data ingestion, not tagging

5. Pre-tag validation: detect when input is not a garment (accessories,
   eyewear, bags, footwear) and return a clear "this product type
   isn't supported" message instead of a half-N/A result.

---

## Update — Playwright Fallback Tested (3 May 2026)

Implemented headless-Chromium fallback (Playwright) for sites where
the fast `requests` path fails. The fallback fires correctly, but
default Playwright doesn't defeat the bot protection on the most
aggressive retailers.

### Test results

| Site | Fast path | Playwright fallback | Outcome |
|---|---|---|---|
| ASOS | ReadTimeout | Triggered, blocked | 400 |
| Net-a-Porter | ReadTimeout | Triggered, blocked | 400 |
| COS | HTTPError | Triggered, blocked | 400 |

All three sites detect headless Chromium and refuse to serve the
page even via the browser. Likely defenses: Datadome, Cloudflare bot
management, or similar fingerprint-based detection.

### Conclusion

The fallback architecture is correct: fast path → graceful degradation
to headless browser → clean error if both fail. But headless browsers
alone are not sufficient for production-grade scraping of major
fashion retailers.

### What would actually work (v3 territory)

- **playwright-stealth plugin** to mask headless fingerprints
- **Residential proxy network** (e.g. Bright Data, Oxylabs) — IP
  rotation defeats most Cloudflare-class defenses
- **Paid scraping API** (ScrapingBee, ScraperAPI) — shifts the
  bot-evasion arms race onto a vendor, ~$0.001–0.005 per request
- **Custom Chromium build** with patched fingerprints — doable but
  high maintenance

### What this means for the project

v2 ships with Playwright fallback as an architectural improvement.
For sites where it doesn't help (the hardest 3), the user gets a
graceful "couldn't load that page" message instead of a hang or
crash. v3 will tackle the bot-evasion layer properly with one of the
approaches above — or, more strategically, will move toward
fine-tuned models on a curated dataset where we own the images.
