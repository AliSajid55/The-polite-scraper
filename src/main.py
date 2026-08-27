"""Books to Scrape - Polite Scraper (Step 2: Crawl 3 catalogue pages)"""

import os
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# --- Configuration ---
BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
SITE_ROOT = "https://books.toscrape.com/"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
USER_AGENT = "FlyRankInternshipA9/1.0 (https://github.com/your-repo)"
TIMEOUT = 10  # seconds
MAX_PAGES = 3
DELAY = 0.5  # seconds between real (non-cached) requests


def ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def cache_path_for_url(url: str) -> str:
    """Derive a cache file path from a catalogue URL."""
    # e.g. .../catalogue/page-1.html -> catalogue-page-1.html
    filename = url.split("/")[-1]  # page-1.html
    return os.path.join(CACHE_DIR, f"catalogue-{filename}")


def load_cache(file_path: str) -> str | None:
    """Load cached HTML from disk."""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def save_cache(file_path: str, content: str) -> None:
    """Save HTML to cache on disk."""
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
        size_kb = len(cached.encode("utf-8")) / 1024
        print(f"  CACHE HIT - {size_kb:.1f} KB from {os.path.basename(cache_file)}")
        return cached

    # Real request — respect delay
    time.sleep(DELAY)
    print(f"  FETCHING - {url}")
    html = fetch_page(url)
    size_kb = len(html.encode("utf-8")) / 1024
    print(f"  FETCHED  - {size_kb:.1f} KB")
    save_cache(cache_file, html)
    return html


def extract_book_links(html: str, page_url: str) -> list[str]:
    """Extract all book links from a catalogue page and return absolute URLs."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for tag in soup.select("article.product_pod h3 a"):
        href = tag.get("href")
        if isinstance(href, str):
            absolute = urljoin(page_url, href)
            links.append(absolute)
    return links


def find_next_page(html: str, current_url: str) -> str | None:
    """Follow the catalogue's own 'next' link. Returns absolute URL or None."""
    soup = BeautifulSoup(html, "html.parser")
    next_btn = soup.select_one("li.next a")
    if next_btn:
        href = next_btn.get("href")
        if isinstance(href, str):
            return urljoin(current_url, href)
    return None


def main():
    """Main entry point — crawl up to MAX_PAGES catalogue pages."""
    ensure_cache_dir()

    all_links: list[str] = []
    current_url = BASE_URL
    page_num = 0

    for page_num in range(1, MAX_PAGES + 1):
        print(f"\n--- Page {page_num} ---")
        html = get_page(current_url)

        # Extract book links
        page_links = extract_book_links(html, current_url)
        all_links.extend(page_links)
        print(f"  Found {len(page_links)} book links on this page")

        # Find next page (unless this is the last page we want)
        if page_num < MAX_PAGES:
            next_url = find_next_page(html, current_url)
            if next_url:
                current_url = next_url
            else:
                print("  No next page found — stopping early")
                break

    # Deduplicate while preserving order
    unique_links = list(dict.fromkeys(all_links))

    # Checkpoint
    print(f"\n{'='*40}")
    print(f"catalogue_pages={page_num}")
    print(f"discovered={len(all_links)}")
    print(f"unique_urls={len(unique_links)}")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
