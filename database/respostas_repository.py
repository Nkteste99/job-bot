from typing import Optional

from .db import db


def get_resposta(pergunta: str) -> Optional[str]:
    if not db.client:
        raise RuntimeError("Supabase client is not initialized")
    try:
        res = (
            db.client.table("respostas_perguntas")
            .select("resposta")
            .filter("pergunta", "eq", pergunta)
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    if not getattr(res, "data", None):
        return None
    return res.data[0].get("resposta")

def save_resposta(pergunta: str, resposta: str) -> bool:
    if not db.client:
        raise RuntimeError("Supabase client is not initialized")
    try:
        db.client.table("respostas_perguntas").insert({
            "pergunta": pergunta,
            "resposta": resposta,
        }).execute()
        return True
    except Exception:
        return False