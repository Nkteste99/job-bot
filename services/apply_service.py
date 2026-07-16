import logging
from typing import Any, Dict, List, Optional, Tuple

import time
from notifier.telegram import send_message

import requests

from database.candidaturas_repository import get_candidaturas_by_vaga_id, insert_candidatura
from database.respostas_repository import get_resposta, save_resposta
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
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Retorna (questions, formId). formId pode ser None se não houver perguntas."""
    url = (
        f"{GUPY_API_BASE}/question-forms/candidates/applications/"
        f"{application_id}/steps/{register_step_id}/forms"
    )
    response = session.get(url, headers=_json_headers(session), timeout=30)
    if response.status_code == 404:
        logger.info("Sem perguntas para applicationId=%s — continuando", application_id)
        return [], None
    response.raise_for_status()
    payload = response.json()
    question_form = payload.get("questionForm") or {}
    form_id = question_form.get("formId")
    questions = question_form.get("questions") or []
    return questions, form_id


def _opt_label(opt: Any) -> str:
    """Extrai o label legível de uma opção da API Gupy."""
    if isinstance(opt, str):
        return opt
    if isinstance(opt, dict):
        for key in ("label", "name", "text", "title", "description"):
            val = opt.get(key)
            if val:
                return str(val)
    return str(opt)


def _opt_value(opt: Any) -> str:
    """Extrai o valor/ID de uma opção da API Gupy."""
    if isinstance(opt, str):
        return opt
    if isinstance(opt, dict):
        for key in ("value", "id", "optionId", "option_id"):
            val = opt.get(key)
            if val is not None:
                return str(val)
    return _opt_label(opt)


def _submit_answers(
    session: requests.Session, application_id: int, register_step_id: int,
    form_id: int, questions: List[Dict[str, Any]], answers_map: Dict[int, str]
) -> bool:
    """Envia as respostas para a API da Gupy via POST /forms/{formId}/reply."""
    if not form_id or not answers_map:
        return True

    payload_questions = []
    for q in questions:
        qid = q.get("questionId")
        cfid = q.get("customFieldId")
        if qid is None or cfid is None:
            continue
        if qid in answers_map:
            payload_questions.append({
                "questionId": qid,
                "customFieldId": cfid,
                "answers": [answers_map[qid]],
            })

    if not payload_questions:
        return True

    url = (
        f"{GUPY_API_BASE}/question-forms/candidates/applications/"
        f"{application_id}/steps/{register_step_id}/forms/{form_id}/reply"
    )
    response = session.post(
        url,
        json={"questionForm": {"questions": payload_questions}},
        headers=_json_headers(session),
        timeout=30,
    )
    if response.status_code == 200:
        print(f"✅ Respostas enviadas para a API ({len(payload_questions)} perguntas)")
        return True
    else:
        print(f"⚠️  Erro ao enviar respostas: HTTP {response.status_code}")
        logger.warning("Erro ao enviar respostas: %s %s", response.status_code, response.text[:500])
        return False


def _submit_additional_info(session: requests.Session, application_id: int) -> bool:
    """Envia informações adicionais (como ouviu falar, se é funcionário, etc.)."""
    url = f"{GUPY_API_BASE}/curriculum-management/candidate/curriculum/{application_id}/additional-info"
    response = session.put(
        url,
        json={
            "howDidYouHearAboutUs": "portal_de_vagas_da_gupy",
            "howDidYouHearAboutUsDescription": "Gupy Job Portal",
            "isCompanyEmployee": False,
            "corporateEmail": "",
            "isIndicated": False,
            "isIndicatedBy": None,
            "identityCardNumber": "",
        },
        headers=_json_headers(session),
        timeout=30,
    )
    return response.status_code in (200, 204)


def _submit_consent(session: requests.Session, application_id: int) -> bool:
    """Envia consentimento (necessário em alguns processos)."""
    url = f"{GUPY_API_BASE}/consent-engine/candidate/user-consent"
    response = session.put(
        url,
        json={"consentGiven": True},
        headers=_json_headers(session),
        timeout=30,
    )
    return response.status_code in (200, 204)


def _process_questions(
    questions: List[Dict[str, Any]],
    empresa: str = None,
    titulo: str = None,
    localizacao: str = None,
    descricao: str = None,
    vaga_num: int = None,
    total_vagas: int = None,
) -> Tuple[List[str], Dict[int, str]]:
    """Processa perguntas interativamente.

    Retorna (skipped_questions, answers_map) onde answers_map mapeia questionId -> resposta.
    """
    skipped_questions: List[str] = []
    answers_map: Dict[int, str] = {}
    progresso_vaga = f"Vaga {vaga_num}/{total_vagas}" if vaga_num and total_vagas else ""
    cabecalho = (
        f"\n{'='*60}\n"
        f"📋 {progresso_vaga} — {empresa or '?'}\n"
        f"💼 {titulo or '?'}\n"
        f"📍 {localizacao or '?'}\n"
        f"{'='*60}"
    )
    print(cabecalho)
    contexto = f"[{progresso_vaga} — {empresa or '?'} — {titulo or '?'}]"
    total_perguntas = len(questions)

    for i, question in enumerate(questions, 1):
        title = question.get("title") or ""
        qid = question.get("questionId")
        required = question.get("required", False)
        qtype = (question.get("type") or "TEXT").upper()
        options = question.get("options") or []

        if not title or qid is None:
            continue

        tag_obrigatorio = " ⚠️  OBRIGATÓRIO" if required else " (opcional)"

        # Tentar resposta salva no banco
        resposta = get_resposta(title)
        if resposta is not None:
            print(f"✅ Resposta encontrada no banco: '{title}' → '{resposta}'")
            answers_map[qid] = resposta
            continue

        print(f"\n{contexto}")
        print(f"❓ Pergunta {i}/{total_perguntas}{tag_obrigatorio}: {title}")

        # Se tem opções E é tipo SELECT/MULTIPLE_CHOICE/CHECKBOX → menu numérico
        tem_opcoes = bool(options) and qtype in ("SELECT", "MULTIPLE_CHOICE", "CHECKBOX")

        if tem_opcoes:
            for idx, opt in enumerate(options, 1):
                print(f"   {idx} - {_opt_label(opt)}")

            if qtype == "CHECKBOX":
                raw = input(f"👉 Números separados por vírgula (ex: 1,3): ").strip()
                if raw:
                    indices = [s.strip() for s in raw.split(",") if s.strip().isdigit()]
                    valores = []
                    labels = []
                    for idx_str in indices:
                        idx = int(idx_str)
                        if 1 <= idx <= len(options):
                            chosen = options[idx - 1]
                            valores.append(_opt_value(chosen))
                            labels.append(_opt_label(chosen))
                    if valores:
                        answers_map[qid] = ",".join(valores)
                        save_resposta(title, ",".join(valores))
                        print(f"✅ Selecionadas: {', '.join(labels)}")
                    else:
                        print("❌ Nenhuma opção válida")
                        if required:
                            skipped_questions.append(title)
                            print("❌ Obrigatória ignorada — inscrição pode ficar incompleta")
                        else:
                            skipped_questions.append(title)
                            print("⏭️  Pulado (opcional)")
                elif not required:
                    skipped_questions.append(title)
                    print("⏭️  Pulado (opcional)")
                else:
                    skipped_questions.append(title)
                    print("❌ Obrigatória ignorada — inscrição pode ficar incompleta")
            else:
                # SELECT / MULTIPLE_CHOICE (seleção única)
                resposta = input(f"👉 Escolha o número (1-{len(options)}): ").strip()
                if resposta.isdigit() and 1 <= int(resposta) <= len(options):
                    chosen = options[int(resposta) - 1]
                    answers_map[qid] = _opt_value(chosen)
                    save_resposta(title, _opt_value(chosen))
                    print(f"✅ Opção {resposta} selecionada: {_opt_label(chosen)}")
                elif not resposta and not required:
                    skipped_questions.append(title)
                    print("⏭️  Pulado (opcional)")
                else:
                    print("❌ Opção inválida")
                    if required:
                        skipped_questions.append(title)
                        print("❌ Obrigatória ignorada — inscrição pode ficar incompleta")
                    else:
                        skipped_questions.append(title)
                        print("⏭️  Pulado (opcional)")
            continue

        # Texto livre (TEXT / TEXT_AREA) — inclui CHECKBOX/SELECT sem opções
        if qtype in ("SELECT", "MULTIPLE_CHOICE", "CHECKBOX") and not options:
            print("   (API não retornou opções — digite sua resposta como texto)")

        placeholder = "Enter para pular" if not required else "⚠️  OBRIGATÓRIO — digite algo"
        resposta = input(f"👉 Sua resposta ({placeholder}): ").strip()

        if resposta:
            # Confirmação antes de salvar
            print(f"\n📝 Você digitou: \"{resposta}\"")
            confirma = input("   Confirmar? (S/n): ").strip().lower()
            if confirma == "n":
                resposta = input("   Digite novamente (ou Enter para pular): ").strip()
                if not resposta:
                    if required:
                        skipped_questions.append(title)
                        print("❌ Obrigatória ignorada — inscrição pode ficar incompleta")
                    else:
                        skipped_questions.append(title)
                        print("⏭️  Pulado (opcional)")
                    continue

            answers_map[qid] = resposta
            save_resposta(title, resposta)
            print(f"✅ Resposta salva no banco para uso futuro!")
        elif required:
            resposta_manual = input("⚠️  Essa pergunta é obrigatória. Digite sua resposta: ").strip()
            if resposta_manual:
                print(f"\n📝 Você digitou: \"{resposta_manual}\"")
                confirma = input("   Confirmar? (S/n): ").strip().lower()
                if confirma == "n":
                    resposta_manual = input("   Digite novamente: ").strip()
                if resposta_manual:
                    answers_map[qid] = resposta_manual
                    save_resposta(title, resposta_manual)
                    print(f"✅ Resposta salva!")
                else:
                    skipped_questions.append(title)
                    print("❌ Obrigatória mas pulada — inscrição pode ficar incompleta")
            else:
                skipped_questions.append(title)
                print("❌ Obrigatória mas pulada — inscrição pode ficar incompleta")
        else:
            skipped_questions.append(title)
            print("⏭️  Pulado (opcional)")

    return skipped_questions, answers_map


def _submit_presentation(session: requests.Session, application_id: int, texto: str) -> bool:
    if not texto:
        return True
    url = f"{GUPY_API_BASE}/application-highlights/{application_id}/presentations"
    response = session.patch(
        url,
        json={"highlightPresentations": [{"type": "text", "content": texto}]},
        headers=_json_headers(session),
        timeout=30,
    )
    return response.status_code == 200


def _submit_skills(session: requests.Session, application_id: int, skill_ids: List[int] = None) -> bool:
    if skill_ids is None:
        skill_ids = [65846884, 65846886, 65846887]  # Python, Linux, AWS
    url = f"{GUPY_API_BASE}/application-highlights/{application_id}/skills"
    response = session.patch(
        url,
        json={"highlightSkills": skill_ids},
        headers=_json_headers(session),
        timeout=30,
    )
    return response.status_code == 200


def _complete_step(session: requests.Session, application_id: int, register_step_id: int) -> Dict[str, Any]:
    """Completa o step e retorna o JSON da resposta (contém registrationComplete)."""
    url = f"{APPLICATION_URL}/{application_id}/{register_step_id}/complete"
    response = session.patch(
        url,
        json={},
        headers=_json_headers(session),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _get_step_status(session: requests.Session, application_id: int) -> Dict[str, Any]:
    """Busca o status atual do step da candidatura."""
    url = f"{APPLICATION_URL}/{application_id}/step"
    response = session.get(url, headers=_json_headers(session), timeout=30)
    response.raise_for_status()
    return response.json()


def _register_candidatura_parcial(job_id: int, application_id: int) -> None:
    """Registra candidatura imediatamente como 'em andamento' para evitar duplicatas."""
    vaga = get_vaga_by_external_id(str(job_id))
    if not vaga:
        return
    candidatura = Candidatura(
        vaga_id=vaga["id"],
        status="em andamento",
        observacoes=f"applicationId={application_id}",
        origem="gupy_api",
    )
    insert_candidatura(candidatura)


def _register_candidatura(job_id: int, application_id: int, registration_complete: bool) -> None:
    """Atualiza candidatura existente com status final."""
    vaga = get_vaga_by_external_id(str(job_id))
    if not vaga:
        return
    status = "Candidatura enviada" if registration_complete else "Candidatura incompleta"
    candidaturas = get_candidaturas_by_vaga_id(vaga["id"])
    for c in candidaturas:
        if c.get("origem") == "gupy_api":
            from database.candidaturas_repository import update_candidatura_status
            update_candidatura_status(c["id"], status, f"applicationId={application_id}")
            return
    # Se não encontrou, cria nova
    candidatura = Candidatura(
        vaga_id=vaga["id"],
        status=status,
        observacoes=f"applicationId={application_id}",
        origem="gupy_api",
    )
    insert_candidatura(candidatura)


def apply_to_job(session: requests.Session, job_id: int, career_page_url: str = None, empresa: str = None, titulo: str = None, localizacao: str = None, descricao: str = None, vaga_num: int = None, total_vagas: int = None) -> dict:
    if _has_existing_candidatura(job_id):
        logger.info("Candidatura já existe para job_id=%s — pulando", job_id)
        return {
            "success": False,
            "applicationId": None,
            "skipped_questions": [],
            "reason": "candidatura_ja_existe",
        }

    # Extrair origin da career_page_url ou do link da vaga
    from urllib.parse import urlparse
    if career_page_url:
        parsed = urlparse(career_page_url)
        company_origin = f"{parsed.scheme}://{parsed.netloc}"
        session.headers.update({
            "origin": company_origin,
            "referer": f"{company_origin}/",
        })
    else:
        # Tentar extrair do link da vaga (ex: https://montreal.gupy.io/job/...)
        vaga_info = get_vaga_by_external_id(str(job_id))
        link = vaga_info.get("link") if vaga_info else None
        if link:
            parsed = urlparse(link)
            company_origin = f"{parsed.scheme}://{parsed.netloc}"
            session.headers.update({
                "origin": company_origin,
                "referer": f"{company_origin}/",
            })

    application = _create_application(session, job_id)
    application_id = application["applicationId"]
    register_step_id = application["registerStepId"]

    # Registrar candidatura IMEDIATAMENTE como "em andamento"
    # Se der Ctrl+C depois, a candidatura fica registrada e não duplica
    _register_candidatura_parcial(job_id, application_id)

    # Enviar resumo da vaga no Telegram
    msg_parts = []
    if vaga_num and total_vagas:
        msg_parts.append(f"📋 Vaga {vaga_num}/{total_vagas}")
    if empresa:
        msg_parts.append(f"🏢 {empresa}")
    if titulo:
        msg_parts.append(f"💼 {titulo}")
    if localizacao:
        msg_parts.append(f"📍 {localizacao}")
    if descricao:
        desc_limpa = descricao.strip().replace("<br>", "\n").replace("<br/>", "\n")
        import re
        desc_limpa = re.sub(r"<[^>]+>", "", desc_limpa)
        msg_parts.append(f"\n{desc_limpa[:2000]}")
    send_message("\n".join(msg_parts))
    time.sleep(2)

    questions, form_id = _get_question_forms(session, application_id, register_step_id)
    skipped_questions, answers_map = _process_questions(
        questions, empresa=empresa, titulo=titulo, localizacao=localizacao,
        descricao=descricao, vaga_num=vaga_num, total_vagas=total_vagas,
    )

    # 1. Enviar respostas para a API
    _submit_answers(session, application_id, register_step_id, form_id, questions, answers_map)

    # 2. Info adicional
    _submit_additional_info(session, application_id)

    # 3. Apresentação e skills
    from config.settings import settings
    texto = getattr(settings, "APRESENTACAO_TEXTO", "") or ""
    _submit_presentation(session, application_id, texto)
    _submit_skills(session, application_id)

    # 4. Consentimento
    _submit_consent(session, application_id)

    # 5. Completar step e verificar
    complete_result = _complete_step(session, application_id, register_step_id)
    registration_complete = complete_result.get("registrationComplete", False)

    # 6. Verificação dupla do status
    if not registration_complete:
        step_info = _get_step_status(session, application_id)
        registration_complete = step_info.get("registrationComplete", False)

    # 7. Registrar candidatura com status correto
    _register_candidatura(job_id, application_id, registration_complete)

    if registration_complete:
        print(f"✅ Candidatura ENVIADA E CONFIRMADA — applicationId={application_id}")
        send_message(f"✅ Inscrição confirmada!\n💼 {titulo}\n🏢 {empresa}\napplicationId: {application_id}")
    else:
        print(f"⚠️  Candidatura enviada mas NÃO CONFIRMADA — applicationId={application_id}")
        print("   Verifique manualmente na Gupy se a inscrição ficou completa.")
        send_message(f"⚠️  Inscrição NÃO confirmada!\n💼 {titulo}\n🏢 {empresa}\napplicationId: {application_id}\nVerifique manualmente na Gupy.")

    return {
        "success": registration_complete,
        "applicationId": application_id,
        "skipped_questions": skipped_questions,
        "registrationComplete": registration_complete,
    }
