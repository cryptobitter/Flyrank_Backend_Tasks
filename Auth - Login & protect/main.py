"""
Stage 0: Setup FastAPI Server & Supabase Client.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
import supabase_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = supabase_client.get_supabase_client()
    app.state.supabase = client
    print("Server running and connected to Supabase")
    yield


app = FastAPI(title="Auth Login & Protect API", lifespan=lifespan)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=supabase_client.PORT, reload=True)
