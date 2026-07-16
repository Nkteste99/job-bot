from typing import Tuple
import time
from datetime import datetime

import logging
import sys
from pathlib import Path

import schedule

from collectors.gupy import collect
from models.models import Vaga
from database.vagas_repository import get_vaga_by_external_id, insert_vaga, delete_vaga_by_external_id
from database.candidaturas_repository import cleanup_old_candidaturas, get_candidaturas_by_vaga_id, get_candidaturas_by_status
from notifier.telegram import send_message, notify_new_vagas
from services.gupy_auth import get_session, check_cookie_expiry_and_notify
from services.apply_service import apply_to_job

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
    # Limpar candidaturas antigas (30+ dias) no início de cada execução
    try:
        removed = cleanup_old_candidaturas(dias=30)
        if removed:
            logging.info(f"Limpeza: {removed} candidaturas antigas removidas (>30 dias)")
    except Exception:
        pass

    vagas = collect(cargo, localizacao)
    if limite_teste and limite_teste > 0:
        vagas = vagas[:limite_teste]
    inserted = 0
    existing = 0
    candidaturas_enviadas = 0
    candidaturas_falharam = 0
    global _seen_external_ids
    try:
        _seen_external_ids
    except NameError:
        _seen_external_ids = set()

    vagas_novas = []
    for v in vagas:
        if not v.external_id:
            continue
        key = str(v.external_id)
        if key in _seen_external_ids:
            continue
        vaga_db = get_vaga_by_external_id(key)
        if vaga_db:
            candidaturas = get_candidaturas_by_vaga_id(vaga_db["id"])
            if candidaturas:
                continue
        vagas_novas.append(v)
    total_novas = len(vagas_novas)
    vaga_atual = 0

    for vaga in vagas:
        try:
            if vaga.external_id:
                key = str(vaga.external_id)
                # Se já foi processada nesta execução, pula
                if key in _seen_external_ids:
                    existing += 1
                    continue
                # Se a vaga existe no banco, verificar se tem candidatura
                vaga_db = get_vaga_by_external_id(key)
                if vaga_db:
                    candidaturas = get_candidaturas_by_vaga_id(vaga_db["id"])
                    if candidaturas:
                        existing += 1
                        continue
                    # Vaga existe mas sem candidatura → ainda precisa processar
            insert_vaga(vaga)
            if vaga.external_id:
                _seen_external_ids.add(str(vaga.external_id))
            inserted += 1
            vaga_atual += 1
            print(f"\n📋 Vaga {vaga_atual}/{total_novas} — {vaga.empresa} — {vaga.titulo}")

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
                if vaga.external_id:
                    delete_vaga_by_external_id(vaga.external_id)
                continue

            try:
                session = get_session()
                result = apply_to_job(session, int(vaga.external_id), career_page_url=vaga.career_page_url, empresa=vaga.empresa, titulo=vaga.titulo, localizacao=vaga.localizacao, descricao=vaga.descricao, vaga_num=vaga_atual, total_vagas=total_novas)
                if result and result.get("success"):
                    candidaturas_enviadas += 1
                else:
                    candidaturas_falharam += 1
            except Exception as e:
                candidaturas_falharam += 1
                logging.warning(f"Candidatura falhou para {vaga.external_id}: {e}")

            # Deletar vaga do banco depois de processar (sucesso ou falha)
            if vaga.external_id:
                delete_vaga_by_external_id(vaga.external_id)

        except Exception:
            continue

    # Resumo
    try:
        resumo = (
            f"✅ Coleta concluída:\n"
            f"📋 {inserted} novas vagas encontradas\n"
            f"⏭️ {existing} já existiam\n"
            f"✅ {candidaturas_enviadas} candidaturas enviadas\n"
            f"❌ {candidaturas_falharam} candidaturas falharam"
        )
        send_message(resumo)
    except Exception:
        pass

    return inserted, existing


def run_apply_only(limite: int = None) -> Tuple[int, int]:
    """Candidata-se às vagas que já estão no banco mas não têm candidatura.
    Não coleta novas vagas da API.
    Filtra vagas senior+.

    Returns: (enviadas, falharam)
    """
    from database.vagas_repository import get_all_vagas

    vagas_db = get_all_vagas()

    # Filtro de senioridade
    senior_keywords = [
        " senior", "sênior", " sr.", " sr ", " sr/", "-sr",
        " specialist", "especialista",
        " lead", "líder",
        " head", " principal", " staff",
        " diretor", "director",
        " gerente", "manager",
        " tech lead", " engineering manager",
    ]
    vagas_filtradas = []
    for v in vagas_db:
        titulo = (v.get("titulo") or "").lower()
        desc = (v.get("descricao") or "").lower()
        texto = titulo + " " + desc
        if any(k in texto for k in senior_keywords):
            continue
        vagas_filtradas.append(v)
    vagas_db = vagas_filtradas

    if limite and limite > 0:
        vagas_db = vagas_db[:limite]

    enviadas = 0
    falharam = 0
    total = len(vagas_db)

    for i, vaga in enumerate(vagas_db, 1):
        vaga_id = vaga.get("id")
        external_id = vaga.get("external_id")

        if not external_id:
            continue

        candidaturas = get_candidaturas_by_vaga_id(vaga_id)
        if candidaturas:
            continue

        print(f"\n📋 Vaga {i}/{total} — {vaga.get('empresa')} — {vaga.get('titulo')}")
        try:
            session = get_session()
            result = apply_to_job(
                session, int(external_id),
                empresa=vaga.get("empresa"),
                titulo=vaga.get("titulo"),
                localizacao=vaga.get("localizacao"),
                descricao=vaga.get("descricao"),
                vaga_num=i, total_vagas=total,
            )
            if result and result.get("success"):
                enviadas += 1
            else:
                falharam += 1
        except Exception as e:
            falharam += 1
            logging.warning(f"Candidatura falhou para {external_id}: {e}")

    resumo = f"✅ Candidaturas:\n✅ {enviadas} enviadas\n❌ {falharam} falharam"
    send_message(resumo)
    print(resumo)
    return enviadas, falharam


def run_resume_pending(limite: int = None) -> Tuple[int, int]:
    """Retoma candidaturas 'em andamento' — tenta completar o fluxo de inscrição.

    Returns: (completas, falharam)
    """
    pendentes = get_candidaturas_by_status("em andamento")
    if limite and limite > 0:
        pendentes = pendentes[:limite]

    completas = 0
    falharam = 0
    total = len(pendentes)

    if total == 0:
        print("Nenhuma candidatura 'em andamento' encontrada.")
        send_message("Nenhuma candidatura pendente para retomar.")
        return 0, 0

    print(f"Encontradas {total} candidaturas pendentes")

    for i, cand in enumerate(pendentes, 1):
        vaga_id = cand.get("vaga_id")
        obs = cand.get("observacoes") or ""

        # Extrair applicationId das observações
        application_id = None
        if "applicationId=" in obs:
            try:
                application_id = int(obs.split("applicationId=")[1].strip())
            except (ValueError, IndexError):
                pass

        if not application_id:
            print(f"\n⚠️  Candidatura {i}/{total}: applicationId não encontrado nas observações")
            falharam += 1
            continue

        # Buscar dados da vaga
        vaga_db = get_vaga_by_external_id(str(vaga_id)) if vaga_id else None
        # Tentar buscar pelo external_id se vaga_db for None
        if not vaga_db and vaga_id:
            from database.db import db
            try:
                res = db.client.table("vagas").select("*").eq("id", vaga_id).limit(1).execute()
                vaga_db = res.data[0] if res.data else None
            except Exception:
                pass

        empresa = vaga_db.get("empresa") if vaga_db else "?"
        titulo = vaga_db.get("titulo") if vaga_db else "?"

        print(f"\n📋 Candidatura {i}/{total} — {empresa} — {titulo}")
        print(f"   applicationId: {application_id}")

        try:
            session = get_session()
            # Verificar status atual na Gupy
            from services.apply_service import _get_step_status, _complete_step, _register_candidatura
            step_info = _get_step_status(session, application_id)
            registration_complete = step_info.get("registrationComplete", False)

            if registration_complete:
                print(f"   ✅ Já estava completa na Gupy — atualizando status")
                from database.candidaturas_repository import update_candidatura_status
                update_candidatura_status(cand["id"], "Candidatura enviada", f"applicationId={application_id}")
                completas += 1
                continue

            # Tentar completar o step de registro
            job_steps = step_info.get("job", {}).get("jobSteps", [])
            register_step = None
            for step in job_steps:
                if step.get("type") == "register":
                    register_step = step
                    break

            if not register_step:
                print(f"   ⚠️  Step de registro não encontrado")
                falharam += 1
                continue

            app_step = register_step.get("applicationStep", {})
            register_step_id = app_step.get("id")

            if not register_step_id:
                print(f"   ⚠️  applicationStep.id não encontrado")
                falharam += 1
                continue

            # Completar step
            complete_result = _complete_step(session, application_id, register_step_id)
            registration_complete = complete_result.get("registrationComplete", False)

            if registration_complete:
                print(f"   ✅ Candidatura completada com sucesso!")
                from database.candidaturas_repository import update_candidatura_status
                update_candidatura_status(cand["id"], "Candidatura enviada", f"applicationId={application_id}")
                completas += 1
            else:
                print(f"   ⚠️  Ainda não confirmada — verifique manualmente na Gupy")
                falharam += 1

        except Exception as e:
            falharam += 1
            print(f"   ❌ Erro: {e}")
            logging.warning(f"Erro ao retomar candidatura {cand.get('id')}: {e}")

    resumo = f"🔄 Retomada de candidaturas:\n✅ {completas} completadas\n❌ {falharam} falharam"
    send_message(resumo)
    print(resumo)
    return completas, falharam


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
    _log("Agendador ativo: coleta a cada 1 hora")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        _log("Agendador interrompido pelo usuário")
