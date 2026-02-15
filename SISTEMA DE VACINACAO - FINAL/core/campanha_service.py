"""
campanha_service.py - Serviço de campanhas de vacinação
"""

from datetime import date
from typing import List

from core.auth_service import AuditLog  # CORRIGIDO: import absoluto com core.


class CampanhasService:
    def __init__(self, db: "Database", audit: AuditLog) -> None:
        self.db = db
        self.audit = audit

    def criar_campanha(
        self,
        nome: str,
        vacina: str,
        publico_alvo: List[str],
        data_inicio: date,
        data_fim: date,
        status: str,
        descricao: str,
        usuario: str,
    ) -> None:
        publico = ",".join(publico_alvo) if publico_alvo else "Todos"
        self.db.execute(
            """
            INSERT INTO campanhas
            (nome_campanha, vacina, publico_alvo, data_inicio, data_fim, status, descricao, usuario_criacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (nome, vacina, publico, data_inicio.isoformat(), data_fim.isoformat(), status, descricao, usuario),
        )
        self.audit.registrar(usuario, "CAMPANHAS", "Criou nova campanha", nome)