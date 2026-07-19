from typing import Optional
from difflib import SequenceMatcher
import unicodedata
import re
import logging

from .db import db

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Normaliza texto: lowercase, remove acentos, pontuação, espaços extras."""
    text = text.lower().strip()
    # Remove acentos
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Remove pontuação e caracteres especiais
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    # Colapsa espaços múltiplos
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def get_resposta(pergunta: str) -> Optional[str]:
    """Busca resposta por similaridade. Threshold: 0.75."""
    if not db.client:
        raise RuntimeError("Supabase client is not initialized")

    pergunta_norm = _normalize(pergunta)

    try:
        res = (
            db.client.table("respostas_perguntas")
            .select("pergunta,resposta")
            .execute()
        )
    except Exception:
        return None

    if not getattr(res, "data", None):
        return None

    best_match = None
    best_score = 0.0

    for row in res.data:
        stored_norm = _normalize(row.get("pergunta", ""))
        score = _similarity(pergunta_norm, stored_norm)
        if score > best_score:
            best_score = score
            best_match = row.get("resposta")

    if best_score >= 0.75 and best_match:
        logger.info(
            "Resposta encontrada (similaridade=%.2f): pergunta='%s' -> '%s'",
            best_score, pergunta, best_match[:50],
        )
        return best_match

    logger.info(
        "Nenhuma resposta similar encontrada (melhor=%.2f): '%s'",
        best_score, pergunta,
    )
    return None

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