import uuid
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from core.config import settings

COLLECTION_TENDERS = "tenders"
COLLECTION_PROFILES = "profiles"

_openai_client: AsyncOpenAI | None = None
_qdrant_client: AsyncQdrantClient | None = None


def get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def get_qdrant() -> AsyncQdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _qdrant_client


async def ensure_qdrant_collections():
    q = get_qdrant()
    existing = {c.name for c in (await q.get_collections()).collections}
    if COLLECTION_TENDERS not in existing:
        await q.create_collection(
            COLLECTION_TENDERS,
            vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
        )
    if COLLECTION_PROFILES not in existing:
        await q.create_collection(
            COLLECTION_PROFILES,
            vectors_config=VectorParams(size=settings.embedding_dim, distance=Distance.COSINE),
        )


async def embed_text(text: str) -> list[float]:
    response = await get_openai().embeddings.create(
        input=text[:8000],
        model=settings.embedding_model,
    )
    return response.data[0].embedding


async def embed_tender(tender_id: str, title: str, description: str | None) -> str:
    """Embed a tender and store in Qdrant. Returns point ID."""
    text = f"{title}. {description or ''}".strip()
    vector = await embed_text(text)

    point_id = str(uuid.uuid4())
    await get_qdrant().upsert(
        collection_name=COLLECTION_TENDERS,
        points=[PointStruct(id=point_id, vector=vector, payload={"tender_id": tender_id})],
    )
    return point_id


async def embed_company_profile(profile) -> str:
    """Embed a company profile and store in Qdrant. Returns point ID."""
    from sqlalchemy.ext.asyncio import AsyncSession

    parts = [profile.company_name or ""]
    if profile.transformer_types:
        parts.append("Transformer types: " + ", ".join(profile.transformer_types))
    if profile.power_kva_min or profile.power_kva_max:
        parts.append(f"Power range: {profile.power_kva_min or 0}-{profile.power_kva_max or 99999} kVA")
    if profile.voltage_kv:
        parts.append("Voltage: " + ", ".join(str(v) for v in profile.voltage_kv) + " kV")
    if profile.keywords_extra:
        parts.append("Keywords: " + ", ".join(profile.keywords_extra))
    if profile.certifications:
        parts.append("Certifications: " + ", ".join(profile.certifications))

    text = ". ".join(p for p in parts if p)
    if not text.strip():
        return ""

    vector = await embed_text(text)
    point_id = str(profile.id)
    await get_qdrant().upsert(
        collection_name=COLLECTION_PROFILES,
        points=[PointStruct(id=point_id, vector=vector, payload={"user_id": str(profile.user_id)})],
    )

    # Update profile_vector_id in DB
    from core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        from crud.users import get_profile
        p = await get_profile(db, profile.user_id)
        if p:
            p.profile_vector_id = point_id
            await db.commit()

    return point_id


async def embed_profile_dict(profile_data: dict) -> str:
    """
    Embed a company profile from a plain dict (no ORM object — safe for background tasks).
    Returns the Qdrant point ID.
    """
    parts = [profile_data.get("company_name") or ""]
    types = profile_data.get("transformer_types") or []
    if types:
        parts.append("Transformer types: " + ", ".join(types))
    kva_min = profile_data.get("power_kva_min")
    kva_max = profile_data.get("power_kva_max")
    if kva_min or kva_max:
        parts.append(f"Power range: {kva_min or 0}-{kva_max or 99999} kVA")
    voltages = profile_data.get("voltage_kv") or []
    if voltages:
        parts.append("Voltage: " + ", ".join(str(v) for v in voltages) + " kV")
    keywords = profile_data.get("keywords_extra") or []
    if keywords:
        parts.append("Keywords: " + ", ".join(keywords))
    certs = profile_data.get("certifications") or []
    if certs:
        parts.append("Certifications: " + ", ".join(certs))

    text = ". ".join(p for p in parts if p)
    if not text.strip():
        return ""

    vector = await embed_text(text)
    point_id = profile_data["id"]
    user_id = profile_data["user_id"]

    await get_qdrant().upsert(
        collection_name=COLLECTION_PROFILES,
        points=[PointStruct(id=point_id, vector=vector, payload={"user_id": user_id})],
    )

    # Update profile_vector_id in DB
    from core.database import AsyncSessionLocal
    import uuid
    async with AsyncSessionLocal() as db:
        from crud.users import get_profile
        p = await get_profile(db, uuid.UUID(user_id))
        if p:
            p.profile_vector_id = point_id
            await db.commit()

    return point_id


async def score_tender_against_profiles(tender_vector: list[float]) -> list[tuple[str, float]]:
    """
    Returns list of (user_id, score) for all profiles that score above threshold.
    """
    if not settings.openai_api_key:
        return []

    results = await get_qdrant().search(
        collection_name=COLLECTION_PROFILES,
        query_vector=tender_vector,
        limit=100,
        score_threshold=settings.match_vector_threshold,
    )
    return [(r.payload["user_id"], r.score) for r in results]
