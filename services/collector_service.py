from typing import Tuple
import time
from datetime import datetime

import logging
import sys
from pathlib import Path

import schedule

from collectors.gupy import collect
from models.models import Vaga
from database.vagas_repository import get_vaga_by_external_id, insert_vaga
from notifier.telegram import send_message, notify_new_vagas
from services.gupy_auth import get_session, check_cookie_expiry_and_notify
from services.apply_service import apply_to_job

# Ensuune logs directory exists at project root and configure logging to file
ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "collector.log"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def run_collection(cargo: str, localizacao: str, limite_teste: int = None) -> Tuple[int, int]:
    """Run collection for given cargo and localizacao.

    Returns a tuple: (inserted_count, existing_count)
    """
    vagas = collect(cargo, localizacao)
    if limite_teste and limite_teste > 0:
        vagas = vagas[:limite_teste]
    inserted = 0
    existing = 0
    # in-process cache of external_ids seen during this process lifetime
    global _seen_external_ids
    try:
        _seen_external_ids
    except NameError:
        _seen_external_ids = set()

    vagas_novas = [v for v in vagas if v.external_id and not get_vaga_by_external_id(str(v.external_id)) and str(v.external_id) not in _seen_external_ids]
    total_novas = len(vagas_novas)
    vaga_atual = 0

    for vaga in vagas:
        try:
            if vaga.external_id:
                key = str(vaga.external_id)
                # check DB first
                if get_vaga_by_external_id(key):
                    existing += 1
                    continue
                # also check local seen set to avoid duplicates within same process
                if key in _seen_external_ids:
                    existing += 1
                    continue
            insert_vaga(vaga)
            if vaga.external_id:
                _seen_external_ids.add(str(vaga.external_id))
            inserted += 1
            vaga_atual += 1
            print(f"\n📋 Vaga {vaga_atual}/{total_novas} — {vaga.empresa} — {vaga.titulo}")
            # Filtro de vagas exclusivas (PcD, cotas, etc.)
            titulo = (vaga.titulo or "").lower()
            descricao = (vaga.descricao or "").lower()
            texto = titulo + " " + descricao
            palavras_exclusivas = [
                "pcd", "pessoa com deficiência", "pessoa com deficiencia",
                "exclusivo para mulher", "exclusivo para mulheres",
                "exclusivo para negro", "exclusivo para negros",
                "cota", "lei 8.213", "laudo médico", "laudo medico",
                "afirmativa", "talentos diversos", "vaga afirmativa"
            ]
            if any(p in texto for p in palavras_exclusivas):
                logging.info(f"Vaga {vaga.external_id} ignorada — exclusiva/cota: {vaga.titulo}")
                continue

            try:
                session = get_session()
                apply_to_job(session, int(vaga.external_id), career_page_url=vaga.career_page_url, empresa=vaga.empresa, titulo=vaga.titulo, localizacao=vaga.localizacao, descricao=vaga.descricao, vaga_num=vaga_atual, total_vagas=total_novas)
            except Exception as e:
                logging.warning(f"Candidatura falhou para {vaga.external_id}: {e}")
        except Exception:
            # ignore individual failures and continue
            continue

    # send notifications
    try:
        summary = f"✅ Coleta concluída: {inserted} novas vagas encontradas, {existing} já existiam."
        send_message(summary)
        if inserted:
            # notify detailed messages for new vagas
            # rebuild list of new vagas from seen ids (approximation)
            new_vagas = [v for v in vagas if v.external_id and str(v.external_id) in _seen_external_ids]
            notify_new_vagas(new_vagas)
    except Exception:
        # don't break execution for notifier errors
        pass

    return inserted, existing


if __name__ == "__main__":
    cargo = "desenvolvedor"
    local = "São Paulo"

    from services.gupy_auth import check_cookie_expiry_and_notify

    def _log(msg: str):
        logging.info(msg)

    def _job():
        check_cookie_expiry_and_notify()
        _log("Coleta iniciada...")
        a, b = run_collection(cargo, local)
        _log(f"Coleta finalizada — Inseridas: {a}, Existentes: {b}")

    # immediate run
    _job()

    # schedule hourly
    schedule.every(1).hours.do(_job)
    _log("Agendador ativo: coleta a cada 1 hora (LIMIT=10 por execução)")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        _log("Agendador interrompido pelo usuário")