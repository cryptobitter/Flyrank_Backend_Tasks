"""
models.py - Pydantic Data Models & Validation Schema for The Polite Scraper
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator, HttpUrl


class BookItem(BaseModel):
    """
    Validated schema representing a single scraped book.
    Ensures rigorous type enforcement, numeric price normalization,
    and rating bounds checking.
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Full title of the book, stripped of surrounding whitespace"
    )
    price: float = Field(
        ...,
        gt=0.0,
        description="Numeric book price parsed from currency text (e.g., 51.77)"
    )
    currency: str = Field(
        default="GBP",
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code (e.g. GBP for £)"
    )
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Star rating converted from word numeral to integer [1..5]"
    )
    is_in_stock: bool = Field(
        ...,
        description="Boolean availability flag parsed from stock status"
    )
    stock_status: str = Field(
        ...,
        min_length=1,
        description="Raw clean availability description (e.g. 'In stock')"
    )
    product_url: str = Field(
        ...,
        min_length=10,
        description="Absolute canonical URL to the book's product detail page"
    )
    image_url: str = Field(
        ...,
        min_length=10,
        description="Absolute URL to the book cover thumbnail image"
    )
    page_number: int = Field(
        ...,
        ge=1,
        description="The catalogue pagination index where this item was found"
    )
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of extraction"
    )

    @field_validator("title")
    @classmethod
    def clean_title(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Title cannot be empty or purely whitespace.")
        return cleaned

    @field_validator("price")
    @classmethod
    def round_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Price cannot be negative.")
        return round(v, 2)


class ScrapeAuditLog(BaseModel):
    """
    Audit log documenting scraping operations, errors, and resilience metrics.
    """
    target_site: str
    user_agent: str
    robots_txt_status: str
    pages_attempted: int
    pages_succeeded: int
    pages_failed: int
    total_books_scraped: int
    total_books_validated: int
    validation_pass_rate_percent: float
    average_price: float
    average_rating: float
    in_stock_count: int
    out_of_stock_count: int
    execution_time_seconds: float
    broken_page_survived: bool
    broken_page_details: Optional[str] = None
