from typing import Tuple

from collectors.gupy import collect
from models.models import Vaga
from database.vagas_repository import get_vaga_by_external_id, insert_vaga
from notifier.telegram import send_message, notify_new_vagas


def run_collection(cargo: str, localizacao: str) -> Tuple[int, int]:
    """Run collection for given cargo and localizacao.

    Returns a tuple: (inserted_count, existing_count)
    """
    vagas = collect(cargo, localizacao)
    inserted = 0
    existing = 0
    # in-process cache of external_ids seen during this process lifetime
    global _seen_external_ids
    try:
        _seen_external_ids
    except NameError:
        _seen_external_ids = set()

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
            # insert and ignore returned value
            insert_vaga(vaga)
            # mark as seen in-memory
            if vaga.external_id:
                _seen_external_ids.add(str(vaga.external_id))
            inserted += 1
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
    print(f"Running collection for {cargo} - {local}")
    a, b = run_collection(cargo, local)
    print(f"Inserted: {a}, Existing: {b}")