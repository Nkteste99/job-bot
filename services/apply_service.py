import logging
from typing import Any, Dict, List

import requests

from database.candidaturas_repository import get_candidaturas_by_vaga_id, insert_candidatura
from database.respostas_repository import get_resposta
from database.vagas_repository import get_vaga_by_external_id
from models.models import Candidatura

logger = logging.getLogger(__name__)

GUPY_API_BASE = "https://private-api.gupy.io"
APPLICATION_URL = f"{GUPY_API_BASE}/selection-process/candidate/application"
PARTNER_NAME = "gupy_portal"


def _json_headers(session: requests.Session) -> Dict[str, str]:
    headers = dict(session.headers)
    headers["content-type"] = "application/json"
    headers["accept"] = "*/*"
    return headers


def _has_existing_candidatura(job_id: int) -> bool:
    vaga = get_vaga_by_external_id(str(job_id))
    if not vaga:
        return False
    candidaturas = get_candidaturas_by_vaga_id(vaga["id"])
    return bool(candidaturas)


def _create_application(session: requests.Session, job_id: int) -> Dict[str, Any]:
    response = session.post(
        APPLICATION_URL,
        json={"jobId": job_id, "partnerName": PARTNER_NAME},
        headers=_json_headers(session),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _get_question_forms(
    session: requests.Session, application_id: int, register_step_id: int
) -> List[Dict[str, Any]]:
    url = (
        f"{GUPY_API_BASE}/question-forms/candidates/applications/"
        f"{application_id}/steps/{register_step_id}/forms"
    )
    response = session.get(url, headers=_json_headers(session), timeout=30)
    response.raise_for_status()
    payload = response.json()
    question_form = payload.get("questionForm") or {}
    return question_form.get("questions") or []


def _process_questions(questions: List[Dict[str, Any]]) -> List[str]:
    skipped_questions: List[str] = []
    for question in questions:
        title = question.get("title") or ""
        if not title:
            continue
        resposta = get_resposta(title)
        if resposta is None:
            logger.warning("Pergunta sem resposta conhecida: %s", title)
            skipped_questions.append(title)
    return skipped_questions


def _advance_step(session: requests.Session, application_id: int) -> Dict[str, Any]:
    url = f"{APPLICATION_URL}/{application_id}/step"
    response = session.get(url, headers=_json_headers(session), timeout=30)
    response.raise_for_status()
    return response.json()


def _register_candidatura(job_id: int, application_id: int) -> None:
    vaga = get_vaga_by_external_id(str(job_id))
    if not vaga:
        return
    candidatura = Candidatura(
        vaga_id=vaga["id"],
        status="Candidatura enviada",
        observacoes=f"applicationId={application_id}",
        origem="gupy_api",
    )
    insert_candidatura(candidatura)


def apply_to_job(session: requests.Session, job_id: int) -> dict:
    if _has_existing_candidatura(job_id):
        logger.info("Candidatura já existe para job_id=%s — pulando", job_id)
        return {
            "success": False,
            "applicationId": None,
            "skipped_questions": [],
            "reason": "candidatura_ja_existe",
        }

    application = _create_application(session, job_id)
    application_id = application["applicationId"]
    register_step_id = application["registerStepId"]

    questions = _get_question_forms(session, application_id, register_step_id)
    skipped_questions = _process_questions(questions)

    step = _advance_step(session, application_id)
    _register_candidatura(job_id, application_id)

    return {
        "success": True,
        "applicationId": application_id,
        "skipped_questions": skipped_questions,
        "step": step,
    }
