from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import create_tables
from routers import auth, tenders, profile, sources


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    # Ensure Qdrant collections exist
    try:
        from ai.embedder import ensure_qdrant_collections
        await ensure_qdrant_collections()
    except Exception as e:
        print(f"[WARNING] Qdrant init failed (will retry on first use): {e}")
    yield


app = FastAPI(
    title="TenderMind API",
    description="Global AI tender monitoring — finds matching tenders worldwide and alerts via Telegram",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://tendermind.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/v1")
app.include_router(tenders.router, prefix="/v1")
app.include_router(profile.router, prefix="/v1")
app.include_router(sources.router, prefix="/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "tendermind-api"}
