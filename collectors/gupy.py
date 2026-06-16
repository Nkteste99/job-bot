"""Gupy collector (V1).

Implements a simple collector using `requests` against the public Gupy
portal API. The collector is defensive: it accepts multiple response shapes
and maps available fields into the `Vaga` model.
"""
from typing import List, Dict

import requests

from models.models import Vaga
from database.vagas_repository import get_vaga_by_external_id, insert_vaga


API_URL = "https://employability-portal.gupy.io/api/v1/jobs"


def _map_job_to_vaga(job: Dict) -> Vaga:
    # Map API fields to Vaga model according to the provided mapping:
    # id -> external_id
    # name -> titulo
    # companyName -> nome real; careerPageName pode trazer slogan/branding
    # jobUrl -> link
    # city + state -> localizacao ("cidade - estado")
    # publishedDate -> data_publicacao
    # description -> descricao
    # fonte -> "gupy"
    external_id = job.get("id")
    titulo = job.get("name")
    empresa = job.get("companyName") or job.get("careerPageName") or job.get("careerPage")
    link = job.get("jobUrl") or job.get("job_url")
    salario = job.get("salary") or job.get("remuneration")
    city = job.get("city", "")
    state = job.get("state", "")
    # Concatenate city and state as requested. If both are empty, leave None.
    if city and state:
        localizacao = f"{city} - {state}"
    elif city:
        localizacao = city
    elif state:
        localizacao = state
    else:
        localizacao = None
    fonte = "gupy"
    data_publicacao = job.get("publishedDate") or job.get("published_date")
    descricao = job.get("description")

    return Vaga(
        external_id=str(external_id) if external_id is not None else None,
        empresa=empresa,
        titulo=titulo,
        link=link,
        salario=salario,
        localizacao=localizacao,
        workplacetype=job.get("workplaceType"),
        fonte=fonte,
        data_publicacao=data_publicacao,
        descricao=descricao,
    )

def collect(cargo: str, localizacao: str, limit: int = 100) -> List[Vaga]:
    """Collect vacancies from Gupy matching `cargo` and `localizacao`.

    For each job returned by the API we map to `Vaga`, avoid duplicates by
    `external_id` and insert new vacancies into the DB via
    `insert_vaga`.
    """
    params = {
        "limit": limit,
        "offset": 0,
        "sortBy": "publishedDate",
        "jobName": cargo,
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(API_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []

    try:
        payload = resp.json()
    except Exception:
        return []

    # the API may return items under different keys; try common possibilities
    items = None
    if isinstance(payload, dict):
        for key in ("data", "items", "results", "jobs", "vacancies"):
            if key in payload and isinstance(payload[key], list):
                items = payload[key]
                break
        if items is None:
            # maybe payload itself is the list
            if any(isinstance(v, dict) for v in payload.values()):
                # flatten possible dict-of-dicts
                items = []
                for v in payload.values():
                    if isinstance(v, list):
                        items.extend(v)
    elif isinstance(payload, list):
        items = payload

    if not items:
        return []

    vagas: List[Vaga] = []
    for job in items:
        try:
            # Filtro de localização: remoto aceita qualquer lugar, presencial/híbrido só SP
            workplace = (job.get("workplaceType") or "").lower()
            state = (job.get("state") or "").strip()
            if workplace != "remote" and state != "São Paulo":
                continue

            vaga = _map_job_to_vaga(job)
            if vaga.external_id:
                existing = get_vaga_by_external_id(vaga.external_id)
                if existing:
                    continue
            inserted = None
            try:
                inserted = insert_vaga(vaga)
            except Exception:
                # if DB insertion fails, skip but still include mapped object
                inserted = None

            # prefer DB-returned dict if available, otherwise mapped Vaga
            vagas.append(vaga)
        except Exception:
            continue

    return vagas


if __name__ == "__main__":
    res = collect("desenvolvedor", "São Paulo")
