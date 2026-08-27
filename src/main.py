"""Books to Scrape - Polite Scraper"""

import os
import requests

# --- Configuration ---
CATALOGUE_URL = "https://books.toscrape.com/catalogue/page-1.html"
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
CACHE_FILE = os.path.join(CACHE_DIR, "catalogue-page-1.html")
USER_AGENT = "FlyRankInternshipA9/1.0 (https://github.com/your-repo)"
TIMEOUT = 10  # seconds


def fetch_page(url: str) -> str:
    """Fetch a page from the web with polite headers."""
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=TIMEOUT)

    if response.status_code != 200:
        raise Exception(f"Failed to fetch: {response.status_code}")

    return response.text


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


def main():
    """Main entry point."""
    # Check cache first
    cached = load_cache(CACHE_FILE)
    if cached:
        size_kb = len(cached.encode("utf-8")) / 1024
        print(f"CACHE HIT - {size_kb:.1f} KB from {CACHE_FILE}")
        return

    # Fetch from web
    print(f"FETCH - {CATALOGUE_URL}")
    html = fetch_page(CATALOGUE_URL)
    size_kb = len(html.encode("utf-8")) / 1024
    print(f"FETCHED - {size_kb:.1f} KB")

    # Save to cache
    save_cache(CACHE_FILE, html)
    print(f"CACHED - {CACHE_FILE}")


if __name__ == "__main__":
    main()
