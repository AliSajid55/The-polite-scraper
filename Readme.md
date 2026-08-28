# Books to Scrape - Polite Scraper

A small, polite web scraping pipeline that downloads book data from Books to Scrape and turns it into clean JSON records.

## Target Classification

| Field | Detail |
|-------|--------|
| **Site** | books.toscrape.com |
| **Why** | Sandbox site built specifically for scraping practice. The site is designed for learners to practice web scraping. |
| **Scope** | First 3 catalogue pages only (60 books) |
| **Data collected** | Book title, price (raw + numeric), availability, rating, description, URL, source page, fetch timestamp |
| **Why appropriate** | This is a sandbox site meant for scraping practice. The site exists so people can learn scraping without affecting real businesses. |

## robots.txt Result

```
404 Not Found
nginx/1.21.6
```

No robots.txt file found. A missing file is not permission — it is just a missing file.

## Promise

I will not reuse this code on another site without checking its rules and terms first.

## How to Run

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/scraper.git
cd scraper

# 2. Create virtual environment and install dependencies
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt

# 3. Run the scraper
python src/main.py
```

## Output Files

| File | Description |
|------|-------------|
| `output/books.json` | Clean, validated records (60 books) |
| `output/run-report.json` | Honest numbers from the last run |
| `output/errors.json` | Validation errors (only if any) |

## Record Schema

Each book record in `books.json` follows this shape:

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_text": "£51.77",
  "price_gbp": 51.77,
  "availability_text": "In stock (22 available)",
  "rating_text": "Three",
  "description": "It's hard to imagine a world without A Light in the Attic...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-08-28T03:21:41Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | Yes | Book title |
| `product_url` | string (https://) | Yes | Canonical URL — unique identity |
| `price_text` | string | Yes | Raw price as displayed on page |
| `price_gbp` | float | Yes | Numeric price for sorting/comparing |
| `availability_text` | string | Yes | Stock availability text |
| `rating_text` | string \| null | No | Star rating word (e.g. "Three") |
| `description` | string \| null | No | Product description (null if missing) |
| `source_page` | string | Yes | Catalogue page where this book was found |
| `fetched_at` | string (ISO-8601) | Yes | UTC timestamp of when the record was fetched |

## Politeness Rules

| Rule | Implementation |
|------|----------------|
| **User-Agent** | `FlyRankInternshipA9/1.0 (https://github.com/your-repo)` — identifies the scraper |
| **Delay** | 0.5 seconds between real (non-cached) requests |
| **Timeout** | 10 seconds per request |
| **Cache** | Pages cached to disk — cached pages need no delay, they never leave your computer |
| **Retry** | Only on timeout or 5xx errors (once). Never retry 404 or 403 |
| **Error handling** | One bad page is logged and skipped — 59 good records survive one bad one |

## Idempotency

Running the scraper twice produces the same 60 records — not 120. The script merges with existing `books.json` using `product_url` as the canonical key. This makes re-running a failed job safe.

## Limitation

The description field is sometimes duplicated on the source page (the full text appears twice in the HTML). This scraper stores the text as-is without deduplicating within the description itself. A production scraper would need to detect and trim this.

## Run Report (Proof)

```json
{
  "start_time": "2026-08-28T03:21:41Z",
  "duration_seconds": 1.6,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": []
}
```

*This run used cached pages (pages_fetched=0, cache_hits=63). A fresh run with no cache would show pages_fetched=63.*

## Why No Browser

The data is already in the HTML the server sends. A browser would only add cost — slower execution, higher memory usage, and a heavier footprint — without extracting any additional information. The HTML contains all the structured data we need.

## Ethics Note

- **Use an official API when one exists.** APIs are the proper way to access data — they respect rate limits and terms of service.
- **Never bypass logins, paywalls, or blocks.** If a site requires authentication or payment, that is a boundary you must respect.
- **Collect only what you need.** Take the minimum data required for your purpose. Scraping everything just because you can is not ethical.
- **Respect the site.** Identify yourself with a user-agent, add delays between requests, and cache aggressively to minimize impact.
