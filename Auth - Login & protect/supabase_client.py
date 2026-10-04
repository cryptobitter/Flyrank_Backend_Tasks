"""
Stage 0: Initialize the Supabase client using SUPABASE_URL and SUPABASE_KEY from .env.
"""

import os
from dotenv import load_dotenv
from supabase import Client, create_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
PORT: int = int(os.getenv("PORT", "3000"))


def get_supabase_client() -> Client:
    """Create and return a configured Supabase client instance."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_KEY in .env. "
            "Copy .env.example to .env and configure your Supabase project credentials."
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)
