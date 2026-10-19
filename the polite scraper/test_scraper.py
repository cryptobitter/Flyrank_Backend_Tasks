"""
test_scraper.py - Comprehensive Unit & Integration Tests for The Polite Scraper
"""

import unittest
from pydantic import ValidationError
from models import BookItem
from scraper import PoliteBookScraper


class TestPoliteScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = PoliteBookScraper(delay_seconds=0.0)

    # -------------------------------------------------------------------------
    # 1. Price Parsing Tests
    # -------------------------------------------------------------------------
    def test_price_parsing_standard_gbp(self):
        price, currency = self.scraper.parse_price("£51.77")
        self.assertEqual(price, 51.77)
        self.assertEqual(currency, "GBP")

    def test_price_parsing_various_formats(self):
        self.assertEqual(self.scraper.parse_price("£10.00"), (10.0, "GBP"))
        self.assertEqual(self.scraper.parse_price(" $24.95 "), (24.95, "USD"))
        self.assertEqual(self.scraper.parse_price("€100.50"), (100.5, "EUR"))

    def test_price_parsing_invalid(self):
        with self.assertRaises(ValueError):
            self.scraper.parse_price("Free")
        with self.assertRaises(ValueError):
            self.scraper.parse_price("")

    # -------------------------------------------------------------------------
    # 2. Rating Parsing Tests
    # -------------------------------------------------------------------------
    def test_rating_parsing(self):
        self.assertEqual(self.scraper.parse_rating(["star-rating", "One"]), 1)
        self.assertEqual(self.scraper.parse_rating(["star-rating", "Two"]), 2)
        self.assertEqual(self.scraper.parse_rating(["star-rating", "Three"]), 3)
        self.assertEqual(self.scraper.parse_rating(["star-rating", "Four"]), 4)
        self.assertEqual(self.scraper.parse_rating(["star-rating", "Five"]), 5)
        self.assertEqual(self.scraper.parse_rating(["star-rating", "Unknown"]), 0)

    # -------------------------------------------------------------------------
    # 3. Availability Parsing Tests
    # -------------------------------------------------------------------------
    def test_availability_parsing(self):
        in_stock, text = self.scraper.parse_availability("\n  In stock\n")
        self.assertTrue(in_stock)
        self.assertEqual(text, "In stock")

        out_stock, text2 = self.scraper.parse_availability("Sold Out")
        self.assertFalse(out_stock)

    # -------------------------------------------------------------------------
    # 4. Pydantic Schema Validation Tests
    # -------------------------------------------------------------------------
    def test_valid_book_schema(self):
        book = BookItem(
            title="A Light in the Attic",
            price=51.77,
            currency="GBP",
            rating=3,
            is_in_stock=True,
            stock_status="In stock",
            product_url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            image_url="https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg",
            page_number=1,
        )
        self.assertEqual(book.title, "A Light in the Attic")
        self.assertEqual(book.price, 51.77)
        self.assertEqual(book.rating, 3)

    def test_invalid_book_schema_rejection(self):
        # Negative price rejected
        with self.assertRaises(ValidationError):
            BookItem(
                title="Bad Book",
                price=-10.0,
                rating=3,
                is_in_stock=True,
                stock_status="In stock",
                product_url="https://example.com",
                image_url="https://example.com/img.jpg",
                page_number=1,
            )

        # Rating out of bounds (> 5) rejected
        with self.assertRaises(ValidationError):
            BookItem(
                title="Bad Rating",
                price=15.0,
                rating=6,
                is_in_stock=True,
                stock_status="In stock",
                product_url="https://example.com",
                image_url="https://example.com/img.jpg",
                page_number=1,
            )

        # Empty title rejected
        with self.assertRaises(ValidationError):
            BookItem(
                title="   ",
                price=15.0,
                rating=2,
                is_in_stock=True,
                stock_status="In stock",
                product_url="https://example.com",
                image_url="https://example.com/img.jpg",
                page_number=1,
            )

    # -------------------------------------------------------------------------
    # 5. Resilience & Broken Page Survival Tests
    # -------------------------------------------------------------------------
    def test_broken_page_404_survival(self):
        """Verifies that an HTTP 404 returns None instead of raising an unhandled exception."""
        result = self.scraper.fetch_page("https://books.toscrape.com/catalogue/page-99999.html")
        self.assertIsNone(result)

    def test_corrupt_html_isolation(self):
        """Verifies that corrupt HTML tags are skipped while valid books are preserved."""
        html = """
        <article class="product_pod">
            <!-- Missing title, bad price -->
            <div class="product_price"><p class="price_color">NOT_A_PRICE</p></div>
        </article>
        <article class="product_pod">
            <div class="image_container">
                <a href="test_book/index.html"><img src="thumb.jpg" alt="Test"></a>
            </div>
            <p class="star-rating Five"></p>
            <h3><a href="test_book/index.html" title="Resilient Book">Resilient Book</a></h3>
            <div class="product_price">
                <p class="price_color">£42.00</p>
                <p class="instock availability">In stock</p>
            </div>
        </article>
        """
        books = self.scraper.extract_books_from_html(html, page_number=1, current_url="https://books.toscrape.com/")
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].title, "Resilient Book")
        self.assertEqual(books[0].price, 42.00)
        self.assertEqual(books[0].rating, 5)


if __name__ == "__main__":
    unittest.main()
