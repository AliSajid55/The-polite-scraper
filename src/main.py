"""Books to Scrape - Polite Scraper (Step 4: Clean, validate, store)"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, field_validator

# --- Configuration ---
BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
USER_AGENT = "FlyRankInternshipA9/1.0 (https://github.com/your-repo)"
TIMEOUT = 10  # seconds
MAX_PAGES = 3
DELAY = 0.5  # seconds between real (non-cached) requests


# --- Pydantic Schema ---


class BookRecord(BaseModel):
    """Schema for a cleaned, validated book record."""

    title: str
    product_url: str
    price_text: str
    price_gbp: float
    availability_text: str
    rating_text: str | None = None
    description: str | None = None
    source_page: str
    fetched_at: str

    @field_validator("product_url")
    @classmethod
    def url_must_be_https(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError(f"URL must start with https://, got: {v}")
        return v

    @field_validator("price_gbp")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"Price must be non-negative, got: {v}")
        return v


# --- Utility functions ---


def ensure_dir(path: str):
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def cache_path_for_url(url: str) -> str:
    """Derive a cache file path from a URL (uses hash to keep filenames short)."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    parts = url.rstrip("/").split("/")
    short_name = parts[-2] if parts[-1] == "index.html" else parts[-1]
    short_name = short_name.replace(".html", "")
    return os.path.join(CACHE_DIR, f"{short_name}_{url_hash}.html")


def load_cache(file_path: str) -> str | None:
    """Load cached content from disk."""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def save_cache(file_path: str, content: str) -> None:
    """Save content to cache on disk."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def fetch_page(url: str) -> str:
    """Fetch a page from the web with polite headers."""
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch {url}: {response.status_code}")
    return response.text


def get_page(url: str) -> str:
    """Get page content: use cache if available, otherwise fetch with delay."""
    cache_file = cache_path_for_url(url)
    cached = load_cache(cache_file)
    if cached:
        return cached

    time.sleep(DELAY)
    print(f"  FETCHING - {url}")
    html = fetch_page(url)
    save_cache(cache_file, html)
    return html


def clean_price(price_text: str) -> float:
    """Convert price_text like '£51.77' to a float 51.77."""
    # Remove currency symbols and whitespace, then convert to float
    cleaned = re.sub(r"[^\d.]", "", price_text)
    return float(cleaned)


# --- Stage 1: Crawl catalogue pages ---


def extract_book_links(html: str, page_url: str) -> list[tuple[str, str]]:
    """Extract book links from a catalogue page.
    Returns list of (absolute_url, source_page) tuples.
    """
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for tag in soup.select("article.product_pod h3 a"):
        href = tag.get("href")
        if isinstance(href, str):
            absolute = urljoin(page_url, href)
            links.append((absolute, page_url))
    return links


def find_next_page(html: str, current_url: str) -> str | None:
    """Follow the catalogue's own 'next' link."""
    soup = BeautifulSoup(html, "html.parser")
    next_btn = soup.select_one("li.next a")
    if next_btn:
        href = next_btn.get("href")
        if isinstance(href, str):
            return urljoin(current_url, href)
    return None


# --- Stage 2: Extract raw records from detail pages ---


def extract_raw_record(html: str, product_url: str, source_page: str) -> dict:
    """Extract the raw record from a book detail page."""
    soup = BeautifulSoup(html, "html.parser")
    product = soup.select_one("div.product_main")

    # Title
    title_tag = product.select_one("h1") if product else None
    title = title_tag.text.strip() if title_tag else ""

    # Price
    price_tag = product.select_one("p.price_color") if product else None
    price_text = price_tag.text.strip() if price_tag else ""

    # Availability
    avail_tag = product.select_one("p.instock.availability") if product else None
    availability_text = avail_tag.text.strip() if avail_tag else ""

    # Rating (second class on p.star-rating, e.g. "Three")
    rating_text = None
    if product:
        rating_tag = product.select_one("p.star-rating")
        if rating_tag:
            classes = rating_tag.get("class")
            if classes:
                for cls in classes:
                    if isinstance(cls, str) and cls != "star-rating":
                        rating_text = cls
                        break

    # Description — found after #product_description div
    description = None
    desc_div = soup.select_one("#product_description")
    if desc_div:
        next_p = desc_div.find_next_sibling("p")
        if next_p:
            description = next_p.text.strip()

    # Fetched timestamp (UTC ISO-8601)
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


# --- Stage 3: Clean, validate, store ---


def load_existing_books() -> dict[str, dict]:
    """Load existing books.json if it exists, keyed by product_url."""
    books_file = os.path.join(OUTPUT_DIR, "books.json")
    if not os.path.exists(books_file):
        return {}
    with open(books_file, "r", encoding="utf-8") as f:
        records = json.load(f)
    return {r["product_url"]: r for r in records}


def save_books(books: dict[str, dict]) -> None:
    """Save books dict to books.json."""
    books_file = os.path.join(OUTPUT_DIR, "books.json")
    with open(books_file, "w", encoding="utf-8") as f:
        json.dump(list(books.values()), f, indent=2, ensure_ascii=False)


def save_errors(errors: list[dict]) -> None:
    """Save validation errors to errors.json."""
    errors_file = os.path.join(OUTPUT_DIR, "errors.json")
    with open(errors_file, "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)


def clean_and_validate(raw_records: list[dict]) -> tuple[dict[str, dict], list[dict]]:
    """Clean raw records, validate with Pydantic, return (valid_books, errors)."""
    valid_books: dict[str, dict] = {}
    errors: list[dict] = []

    for raw in raw_records:
        # Add price_gbp
        try:
            raw["price_gbp"] = clean_price(raw["price_text"])
        except (ValueError, KeyError) as e:
            errors.append({
                "record": raw,
                "error": f"Price cleaning failed: {e}",
            })
            continue

        # Validate with Pydantic
        try:
            book = BookRecord(**raw)
            valid_books[book.product_url] = book.model_dump()
        except Exception as e:
            errors.append({
                "record": raw,
                "error": f"Validation failed: {e}",
            })

    return valid_books, errors


def main():
    """Main entry point — crawl, extract, clean, validate, store."""
    ensure_dir(CACHE_DIR)
    ensure_dir(OUTPUT_DIR)

    # --- Stage 1: Discover all book links ---
    all_links: list[tuple[str, str]] = []
    current_url = BASE_URL
    page_num = 0

    for page_num in range(1, MAX_PAGES + 1):
        print(f"\n--- Page {page_num} ---")
        html = get_page(current_url)

        page_links = extract_book_links(html, current_url)
        all_links.extend(page_links)
        print(f"  Found {len(page_links)} book links on this page")

        if page_num < MAX_PAGES:
            next_url = find_next_page(html, current_url)
            if next_url:
                current_url = next_url
            else:
                print("  No next page found — stopping early")
                break

    # Deduplicate by URL
    seen: dict[str, str] = {}
    for url, source in all_links:
        if url not in seen:
            seen[url] = source
    unique_books = list(seen.items())

    print(f"\n{'='*40}")
    print(f"catalogue_pages={page_num}")
    print(f"discovered={len(all_links)}")
    print(f"unique_urls={len(unique_books)}")
    print(f"{'='*40}")

    # --- Stage 2: Fetch each detail page and extract records ---
    print(f"\n--- Fetching {len(unique_books)} detail pages ---")
    raw_records: list[dict] = []

    for i, (book_url, source_page) in enumerate(unique_books, 1):
        print(f"\n[{i}/{len(unique_books)}] {book_url.split('/')[-2]}")
        html = get_page(book_url)
        record = extract_raw_record(html, book_url, source_page)
        raw_records.append(record)

    print(f"\n{'='*40}")
    print(f"detail_pages={len(raw_records)}")
    print(f"{'='*40}")

    # --- Stage 3: Clean, validate, store ---
    print(f"\n--- Cleaning and validating ---")
    new_books, errors = clean_and_validate(raw_records)

    # Merge with existing books (idempotent — same URL keeps first seen record)
    existing_books = load_existing_books()
    for url, book in new_books.items():
        if url not in existing_books:
            existing_books[url] = book

    save_books(existing_books)
    if errors:
        save_errors(errors)

    # Checkpoint
    all_prices = [b["price_gbp"] for b in existing_books.values()]
    all_urls = list(existing_books.keys())
    https_ok = all(u.startswith("https://") for u in all_urls)
    prices_ok = all(isinstance(p, (int, float)) for p in all_prices)

    print(f"\n{'='*40}")
    print(f"books={len(existing_books)}")
    print(f"price_gbp_all_numbers={prices_ok}")
    print(f"urls_all_https={https_ok}")
    print(f"validation_errors={len(errors)}")
    print(f"{'='*40}")

    # Show sample cleaned record
    sample = list(existing_books.values())[0]
    print(f"\nSAMPLE CLEANED RECORD:")
    print(json.dumps(sample, indent=2))


if __name__ == "__main__":
    main()
