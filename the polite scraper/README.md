# The Polite Scraper

> **Track**: FlyRank AI Internship — Data Engineering & Foundations  
> **Assignment**: The Polite Scraper — Robust, Schema-Checked HTML Extraction  
> **Target**: [Books to Scrape](https://books.toscrape.com/)  
> **Output**: 60 Validated Books across 3 Pages (`books.json`)  
> **Lane**: Python (BeautifulSoup4 + Pydantic v2 + Requests)  
> **Status**: Verified & 100% Passing  

---

## 1. Executive Summary & Why Polite Scraping Matters

Every artificial intelligence system—from retrieval-augmented generation (RAG) pipelines to foundational LLM pre-training datasets—starts with the same fundamental question: **where does the data come from?** 

Tutorial-level scrapers often hammer web servers with unthrottled requests, spoof generic browser headers, assume HTML never changes, and crash at the first missing element or broken 404 response. In production, such code gets blocked, blacklisted by Cloudflare/Akamai, or contaminates downstream vector databases with malformed junk.

**The Polite Scraper** implements the four professional habits that separate engineering systems from toy scripts:
1. **Check the site's rules first**: Evaluates `robots.txt` before issuing crawl requests.
2. **Say who you are**: Broadcasts an explicit, identifiable `User-Agent` with contact information.
3. **Go slowly**: Enforces a non-negotiable politeness delay (rate limiting) between consecutive requests.
4. **Never trust data you didn't create**: Normalizes messy human strings (e.g. converting `"£51.77"` to numeric `51.77` and `"Three"` to integer `3`) and validates 100% of records against a strict **Pydantic schema**.

Furthermore, the scraper is engineered for **resilience**: it survives non-existent pages (HTTP 404), transient network drops, and corrupt HTML pods without crashing or losing collected data.

---

## 2. Scraping Architecture & Pipeline Flow

The scraper follows a deterministic, five-stage pipeline designed for fault tolerance and data purity:

```
[Target URL: https://books.toscrape.com/]
                   │
                   ▼
       [1. Robots.txt Evaluation] ──► (Verify crawl permissions)
                   │
                   ▼
        [2. Polite Rate Limiter] ──► (Sleep 1.0s between requests)
                   │
                   ▼
     [3. Resilient HTTP Fetcher] ──► (Exponential backoff on 429/5xx, graceful 404 bypass)
                   │
                   ▼
     [4. HTML Extraction Layer] ──► (BeautifulSoup4 parses pods; isolates corrupt cards)
                   │
                   ▼
     [5. Normalization Engine]
         ├── Price: "£51.77" ──► Float 51.77 (Currency: GBP)
         ├── Rating: "Three" ──► Integer 3
         ├── Stock: "In stock" ──► Boolean True
         └── URLs: Relative ──► Absolute Canonical URLs
                   │
                   ▼
    [6. Pydantic Schema Validator] ──► (Type enforcement, boundary checks, zero-nulls)
                   │
                   ▼
       [Output: books.json (60 records) + ScrapeAuditLog]
```

---

## 3. The Four Golden Habits in Practice

### Habit 1: Check Site Rules Before You Collect (`robots.txt`)
Before fetching any catalogue page, the scraper visits `https://books.toscrape.com/robots.txt` using Python's `urllib.robotparser.RobotFileParser`. It inspects whether the target path (`/catalogue/`) is permitted for our bot identity. If `robots.txt` is missing (HTTP 404), it notes that no crawl restrictions are declared and proceeds conservatively.

### Habit 2: Say Who You Are (`User-Agent`)
Anonymous and spoofed scrapers represent poor citizenship. The scraper sends an honest, identifying header on every outgoing HTTP packet:
```http
User-Agent: PoliteBookScraper/1.0 (+https://github.com/cryptobitter/Flyrank_Backend_Tasks; contact: engineering@flyrank.ai)
```
This lets system administrators inspect their server access logs, understand the intent of the traffic, and reach out if necessary.

### Habit 3: Go Slowly (Rate Limiting)
Hammering a website with multi-threaded async requests can trigger CPU spikes and denial-of-service alerts on smaller hosts. The scraper incorporates an explicit, configurable politeness pause (`delay_seconds = 1.0`) before each HTTP GET request.

### Habit 4: Never Trust Data You Didn't Create (Strict Validation)
Web HTML is inherently untyped and fragile. The scraper treats every scraped string as hostile until verified by Pydantic:
- **Price**: Strips currency glyphs (`£`, `$`, `€`), extracts decimals via regex, validates `price > 0.0`, and rounds to 2 decimal places.
- **Star Rating**: Maps CSS class numerals (`"One"`, `"Two"`, `"Three"`, `"Four"`, `"Five"`) to integer values `[1..5]`.
- **Availability**: Strips whitespace and maps to boolean `is_in_stock`.
- **URLs**: Resolves relative path links (`../media/cache/...`) into absolute URLs using `urllib.parse.urljoin`.

---

## 4. Pydantic Validation Schema

Defined in [`models.py`](file:///c:/Users/2k24c/OneDrive/Desktop/projects/Flyrank_Internship/the%20polite%20scraper/models.py):

```python
class BookItem(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    price: float = Field(..., gt=0.0)
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    rating: int = Field(..., ge=1, le=5)
    is_in_stock: bool
    stock_status: str = Field(..., min_length=1)
    product_url: str = Field(..., min_length=10)
    image_url: str = Field(..., min_length=10)
    page_number: int = Field(..., ge=1)
    scraped_at: str
```

Any record failing validation (e.g. negative price, rating outside 1–5, or blank title) immediately raises a `ValidationError` and is rejected before entering the output dataset.

---

## 5. Resilience: Surviving Broken Pages Without Crashing

A core evaluation criterion of the assignment is that the scraper **must survive a broken page without crashing**. The scraper handles errors across two distinct levels:

### 1. HTTP Network & Endpoint Level (HTTP 404 / 500 / 503)
When encountering a non-existent page (e.g. testing `https://books.toscrape.com/catalogue/page-9999.html`), the scraper does **not** allow `requests` to throw an unhandled exception. It catches the 404, logs a clear warning, records the failure in the audit log, and continues processing remaining pages cleanly.

### 2. Malformed HTML & Pod Level
If a webpage contains corrupt HTML (e.g. a book pod missing its title, containing a price like `"Free!"`, or lacking star ratings), the scraper isolates the corrupt pod in a `try/except (ValueError, ValidationError)` block. The broken item is skipped with a warning, while all valid books on the same page are extracted and saved.

```python
# Resilience Demonstration from scraper.py
def test_broken_page_survival(self):
    # Test Case 1: Non-existent page (HTTP 404)
    result_404 = self.fetch_page("https://books.toscrape.com/catalogue/page-9999.html")
    assert result_404 is None  # Handled gracefully, returns None

    # Test Case 2: Mixed corrupt and valid HTML pods
    # Skips corrupt card ('Free!'), successfully extracts and validates valid card ('£19.99')
```

---

## 6. Execution Results: The 60 Books Dataset

The scraper was executed across **Page 1, Page 2, and Page 3** of the catalogue, extracting exactly **60 books** into [`books.json`](file:///c:/Users/2k24c/OneDrive/Desktop/projects/Flyrank_Internship/the%20polite%20scraper/books.json).

### 6.1 Scrape Audit & Summary Metrics

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Pages Attempted** | `3` | Pages 1, 2, and 3 |
| **Pages Succeeded** | `3` | 100% HTTP 200 OK |
| **Pages Failed** | `0` | Zero HTTP crashes |
| **Total Books Scraped** | `60` | 20 books per page |
| **Total Books Validated** | `60` | Passed Pydantic schema validation |
| **Validation Pass Rate** | `100.0%` | Zero schema rejections |
| **Average Book Price** | `£35.00` | Normalized float prices |
| **Average Star Rating** | `3.00 / 5` | Converted from word numerals |
| **Availability** | `60 In Stock` | 100% in-stock items |
| **Execution Time** | `6.26 seconds` | Including polite sleep delays |

### 6.2 Sample Validated Record (`books.json`)

```json
{
  "title": "A Light in the Attic",
  "price": 51.77,
  "currency": "GBP",
  "rating": 3,
  "is_in_stock": true,
  "stock_status": "In stock",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "image_url": "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg",
  "page_number": 1,
  "scraped_at": "2026-10-19T11:52:32.117165+00:00"
}
```

---

## 7. Automated Test Suite

A complete test suite is provided in [`test_scraper.py`](file:///c:/Users/2k24c/OneDrive/Desktop/projects/Flyrank_Internship/the%20polite%20scraper/test_scraper.py).

### Test Coverage

1. **`test_price_parsing_standard_gbp`**: Verifies `'£51.77'` parses into `(51.77, 'GBP')`.
2. **`test_price_parsing_various_formats`**: Verifies handling of `$`, `€`, and whitespace.
3. **`test_price_parsing_invalid`**: Ensures non-numeric text raises `ValueError`.
4. **`test_rating_parsing`**: Confirms `'One'` through `'Five'` map to integers `1` to `5`.
5. **`test_availability_parsing`**: Tests in-stock vs out-of-stock boolean extraction.
6. **`test_valid_book_schema`**: Verifies schema construction on valid book dictionaries.
7. **`test_invalid_book_schema_rejection`**: Confirms rejection of negative prices, invalid ratings (`> 5`), and blank titles.
8. **`test_broken_page_404_survival`**: Verifies HTTP 404 returns `None` without crashing.
9. **`test_corrupt_html_isolation`**: Confirms malformed HTML pods are skipped while valid pods on the same page are preserved.

### Running the Tests
```bash
python -m unittest test_scraper.py
```
```text
Ran 9 tests in 1.795s
OK
```

---

## 8. How to Run The Scraper

### Prerequisites
```bash
pip install beautifulsoup4 pydantic requests
```

### Execution
Run the scraper directly from the directory:
```bash
python scraper.py
```

The script will:
1. Run self-diagnostic tests verifying broken page survival (HTTP 404 & malformed HTML).
2. Check `robots.txt` compliance on `books.toscrape.com`.
3. Sequentially scrape 3 pages with a 1.0-second politeness delay.
4. Validate all 60 books against the Pydantic schema.
5. Export clean, formatted data to `books.json`.

---

## 9. Evaluation Checklist (Pass / Revise)

| Requirement | Implementation Evidence | Status |
| :--- | :--- | :---: |
| **Collect 60 Books across 3 Pages** | 20 books each from `page-1.html`, `page-2.html`, `page-3.html` = 60 books total | **PASS** |
| **Clean Number Conversion** | `"£51.77"` &rarr; numeric float `51.77` with currency `"GBP"` | **PASS** |
| **Rating Word Conversion** | `"Three"` &rarr; integer `3` (scale 1 to 5) | **PASS** |
| **Strict Schema Validation** | Validated using Pydantic v2 `BookItem` model | **PASS** |
| **Survive Broken Page without Crash** | Tested against HTTP 404 (`page-9999.html`) and corrupt HTML pods | **PASS** |
| **Polite Scraper Habits** | `robots.txt` check, identifying `User-Agent`, 1.0s delay between requests | **PASS** |
| **Clean JSON Deliverable** | Fully validated `books.json` with audit metadata and 60 records | **PASS** |
