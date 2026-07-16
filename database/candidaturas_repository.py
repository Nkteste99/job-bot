from typing import Optional, List, Dict

from models.models import Candidatura
from .db import db


def insert_candidatura(c: Candidatura) -> Optional[Dict]:
    if not db.client:
        raise RuntimeError("Supabase client is not initialized")
    
    allowed = {
        "vaga_id", "data_aplicacao", "status", "observacoes",
        "ultima_atualizacao", "origem", "tentativas", "erro_ultima_tentativa",
    }
    payload = {k: v for k, v in c.dict(exclude_none=True, exclude={"id"}).items() if k in allowed}
    
    if "data_aplicacao" in payload and payload["data_aplicacao"] is not None:
        payload["data_aplicacao"] = payload["data_aplicacao"].isoformat()

    try:
        db.client.table("candidaturas").insert(payload).execute()
    except Exception as e:
        import traceback
        print(f"ERRO INSERT CANDIDATURA: {e}")
        traceback.print_exc()
        return None

    query = db.client.table("candidaturas").select("*").filter("vaga_id", "eq", payload.get("vaga_id"))
    if payload.get("origem"):
        query = query.filter("origem", "eq", payload.get("origem"))
    res = query.limit(1).execute()
    return res.data[0] if getattr(res, "data", None) else None


def get_candidaturas_by_vaga_id(vaga_id: int) -> List[Dict]:
    if not db.client:
        raise RuntimeError("Supabase client is not initialized")
    res = (
        db.client.table("candidaturas").select("*").filter("vaga_id", "eq", vaga_id).execute()
    )
    return res.data or []


def update_candidatura_status(candidatura_id: int, status: str, observacoes: Optional[str] = None) -> bool:
    if not db.client:
        raise RuntimeError("Supabase client is not initialized")
    payload = {"status": status}
    if observacoes is not None:
        payload["observacoes"] = observacoes
    res = (
        db.client.table("candidaturas").update(payload).eq("id", candidatura_id).execute()
    )
    return bool(getattr(res, "data", None))


def cleanup_old_candidaturas(dias: int = 30) -> int:
    """Deleta candidaturas mais antigas que X dias. Retorna quantas foram deletadas."""
    if not db.client:
        return 0
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    try:
        res = (
            db.client.table("candidaturas")
            .delete()
            .lt("data_aplicacao", cutoff)
            .execute()
        )
        return len(getattr(res, "data", None) or [])
    except Exception:
        return 0


if __name__ == "__main__":
    print("Running candidaturas_repository quick test...")
    from database.db import test_connection

    if not test_connection():
        print("Supabase unreachable — aborting candidaturas_repository test")
    else:
        # Try to find a vaga created by unit test
        from database.vagas_repository import get_vaga_by_external_id

        vaga = get_vaga_by_external_id("unit-test-123")
        if not vaga:
            print("No vaga found for unit-test-123 — insert a vaga first")
        else:
            from models.models import Candidatura

            c = Candidatura(vaga_id=vaga["id"], origem="test")
            inserted = insert_candidatura(c)
            print("Inserted candidatura:", inserted)
            items = get_candidaturas_by_vaga_id(vaga["id"])
            print("Candidaturas for vaga:", items)
            if inserted and inserted.get("id"):
                ok = update_candidatura_status(inserted["id"], "Em análise", "teste")
                print("Update status result:", ok)
