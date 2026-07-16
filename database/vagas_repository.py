from typing import Optional, List, Dict

from models.models import Vaga
from .db import db


def insert_vaga(vaga: Vaga) -> Optional[Dict]:
    payload = vaga.dict(exclude_none=True, exclude={"id"})
    if "data_publicacao" in payload and payload["data_publicacao"] is not None:
        payload["data_publicacao"] = payload["data_publicacao"].isoformat()
    if not db.client:
        raise RuntimeError("Supabase client is not initialized")
    # perform insert (may return empty body / non-JSON response); ignore JSON parse errors
    try:
        db.client.table("vagas").insert(payload).execute()
    except Exception as e:
        import traceback
        print(f"ERRO INSERT VAGA: {e}")
        traceback.print_exc()
    if "external_id" in payload:
        return get_vaga_by_external_id(payload["external_id"])
    # best-effort: return the most recently created vaga matching title+empresa
    res = (
        db.client.table("vagas")
        .select("*")
        .eq("titulo", payload.get("titulo"))
        .eq("empresa", payload.get("empresa"))
        .limit(1)
        .execute()
    )
    return res.data[0] if getattr(res, "data", None) else None


def get_all_vagas() -> List[Dict]:
    if not db.client:
        raise RuntimeError("Supabase client is not initialized")
    res = db.client.table("vagas").select("*").execute()
    return res.data or []


def get_vaga_by_external_id(external_id: str) -> Optional[Dict]:
    if not db.client:
        raise RuntimeError("Supabase client is not initialized")
    key = str(external_id)
    res = (
        db.client.table("vagas").select("*").filter("external_id", "eq", key).limit(1).execute()
    )
    return res.data[0] if getattr(res, "data", None) else None


def delete_vaga_by_id(vaga_id: int) -> bool:
    if not db.client:
        return False
    try:
        db.client.table("vagas").delete().eq("id", vaga_id).execute()
        return True
    except Exception:
        return False


def delete_vaga_by_external_id(external_id: str) -> bool:
    if not db.client:
        return False
    try:
        db.client.table("vagas").delete().eq("external_id", str(external_id)).execute()
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # quick manual test
    print("Running vagas_repository quick test...")
    from database.db import test_connection

    if not test_connection():
        print("Supabase unreachable — aborting vagas_repository test")
    else:
        v = Vaga(external_id="unit-test-123", empresa="unit", titulo="dev", link="http://", fonte="test")
        inserted = insert_vaga(v)
        print("Inserted:", inserted)
        found = get_vaga_by_external_id("unit-test-123")
        print("Found:", found)
