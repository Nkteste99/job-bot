from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Vaga(BaseModel):
    id: Optional[int] = None
    external_id: Optional[str] = None
    empresa: Optional[str] = None
    titulo: Optional[str] = None
    link: Optional[str] = None
    salario: Optional[str] = None
    localizacao: Optional[str] = None
    workplacetype: Optional[str] = None
    career_page_url: Optional[str] = None
    fonte: Optional[str] = None
    data_publicacao: Optional[datetime] = None
    descricao: Optional[str] = None


class Candidatura(BaseModel):
    id: Optional[int] = None
    vaga_id: Optional[int] = None
    data_aplicacao: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Encontrada"
    observacoes: Optional[str] = None
    ultima_atualizacao: Optional[datetime] = None
    origem: Optional[str] = None
    tentativas: int = 0
    erro_ultima_tentativa: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True
        