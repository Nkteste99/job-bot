from datetime import datetime

from collectors.gupy import _map_job_to_vaga

SAMPLE_JOB = {
    "id": 12345,
    "name": "Desenvolvedor Python",
    "companyName": "Empresa Teste",
    "jobUrl": "https://empresa.gupy.io/jobs/12345",
    "city": "São Paulo",
    "state": "São Paulo",
    "publishedDate": "2024-01-15T10:00:00",
    "description": "Descrição da vaga de teste.",
    "workplaceType": "remote",
    "salary": "5000",
}


def test_map_job_to_vaga_maps_all_fields():
    vaga = _map_job_to_vaga(SAMPLE_JOB)

    assert vaga.external_id == "12345"
    assert vaga.titulo == "Desenvolvedor Python"
    assert vaga.empresa == "Empresa Teste"
    assert vaga.link == "https://empresa.gupy.io/jobs/12345"
    assert vaga.localizacao == "São Paulo - São Paulo"
    assert vaga.fonte == "gupy"
    assert vaga.salario == "5000"
    assert vaga.workplaceType == "remote"
    assert vaga.data_publicacao == datetime(2024, 1, 15, 10, 0)
    assert vaga.descricao == "Descrição da vaga de teste."


def test_map_job_to_vaga_uses_city_only_when_state_missing():
    job = {**SAMPLE_JOB, "state": ""}
    vaga = _map_job_to_vaga(job)
    assert vaga.localizacao == "São Paulo"


def test_map_job_to_vaga_falls_back_to_career_page_name():
    job = {k: v for k, v in SAMPLE_JOB.items() if k != "companyName"}
    job["careerPageName"] = "Página de Carreiras"
    vaga = _map_job_to_vaga(job)
    assert vaga.empresa == "Página de Carreiras"
