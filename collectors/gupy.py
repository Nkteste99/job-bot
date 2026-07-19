"""Gupy collector (V1).

Implements a simple collector using `requests` against the public Gupy
portal API. The collector is defensive: it accepts multiple response shapes
and maps available fields into the `Vaga` model.
"""
from typing import List, Dict
import logging
from datetime import datetime, timezone

import requests

from models.models import Vaga

logger = logging.getLogger(__name__)

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
    pagina = 0

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
        except Exception as e:
            logger.warning("Erro na requisição (offset=%d): %s", offset, e)
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
            logger.info("Página %d: 0 itens — fim da paginação", pagina)
            break

        pagina += 1
        itens_nesta_pagina = len(items)
        logger.info("Página %d: %d itens brutos (offset=%d)", pagina, itens_nesta_pagina, offset)

        for job in items:
            try:
                # Filtro de vagas expiradas
                deadline = job.get("applicationDeadline")
                if deadline:
                    try:
                        exp_date = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                        if exp_date < datetime.now(timezone.utc):
                            continue
                    except (ValueError, TypeError):
                        pass  # se não conseguir parsear, não descarta

                workplace = (job.get("workplaceType") or "").lower()
                state = (job.get("state") or "").strip()
                # Presencial: apenas SP. Remoto: qualquer lugar.
                if workplace == "remote":
                    pass  # aceita de qualquer lugar
                elif state != "São Paulo":
                    continue

                # Filtro de senioridade — vagas acima de pleno
                nome = (job.get("name") or "").lower()
                desc = (job.get("description") or "").lower()
                texto_vaga = nome + " " + desc
                senior_keywords = [
                    " senior", "sênior", " sr.", " sr ", " sr/", "-sr",
                    " specialist", "especialista",
                    " lead", "líder",
                    " head",
                    " principal",
                    " staff",
                    " diretor", "director",
                    " gerente", "manager",
                    " tech lead",
                    " engineering manager",
                ]
                if any(k in texto_vaga for k in senior_keywords):
                    continue

                vaga = _map_job_to_vaga(job)
                vagas.append(vaga)
            except Exception:
                continue

        pagination = payload.get("pagination", {})
        total = pagination.get("total", 0)
        offset += limit

        # Condição de parada dupla:
        # 1. Não retornou itens suficientes = última página
        # 2. offset >= total = todas as páginas percorridas
        if itens_nesta_pagina < limit:
            logger.info("Página %d retornou %d itens (limit=%d) — última página", pagina, itens_nesta_pagina, limit)
            break
        if total and offset >= total:
            logger.info("Offset %d >= total %d — fim da paginação", offset, total)
            break

    logger.info("Coleta finalizada: %d vagas filtradas de %d páginas", len(vagas), pagina)
    return vagas


if __name__ == "__main__":
    res = collect("desenvolvedor", "São Paulo")
