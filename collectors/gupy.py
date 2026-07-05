"""Gupy collector (V1).

Implements a simple collector using `requests` against the public Gupy
portal API. The collector is defensive: it accepts multiple response shapes
and maps available fields into the `Vaga` model.
"""
from typing import List, Dict

import requests

from models.models import Vaga


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
        career_page_url=job.get("careerPageUrl"),
        fonte=fonte,
        data_publicacao=data_publicacao,
        descricao=descricao,
    )

def collect(cargo: str, localizacao: str, limit: int = 100) -> List[Vaga]:
    headers = {"User-Agent": "Mozilla/5.0"}
    vagas: List[Vaga] = []
    offset = 0

    while True:
        params = {
            "limit": limit,
            "offset": offset,
            "sortBy": "publishedDate",
            "jobName": cargo,
        }
        try:
            resp = requests.get(API_URL, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception:
            break

        try:
            payload = resp.json()
        except Exception:
            break

        items = None
        if isinstance(payload, dict):
            for key in ("data", "items", "results", "jobs", "vacancies"):
                if key in payload and isinstance(payload[key], list):
                    items = payload[key]
                    break
            if items is None:
                if any(isinstance(v, dict) for v in payload.values()):
                    items = []
                    for v in payload.values():
                        if isinstance(v, list):
                            items.extend(v)
        elif isinstance(payload, list):
            items = payload

        if not items:
            break

        for job in items:
            try:
                workplace = (job.get("workplaceType") or "").lower()
                state = (job.get("state") or "").strip()
                if workplace != "remote" and state != "São Paulo":
                    continue
                vaga = _map_job_to_vaga(job)
                vagas.append(vaga)
            except Exception:
                continue

        pagination = payload.get("pagination", {})
        total = pagination.get("total", 0)
        offset += limit
        if offset >= total:
            break

    return vagas


if __name__ == "__main__":
    res = collect("desenvolvedor", "São Paulo")
