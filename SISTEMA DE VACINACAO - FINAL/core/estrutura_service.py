"""
estrutura_service.py - Serviço de estrutura organizacional
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from core.auth_service import AuditLog  # CORRIGIDO: import absoluto com core.


class EstruturaOrganizacionalService:
    """Serviço para gerenciar a estrutura organizacional"""
    
    def __init__(self, db: "Database", audit: AuditLog) -> None:
        self.db = db
        self.audit = audit
    
    def obter_todas_superintendencias(self) -> List[str]:
        """Obtém todas as superintendências cadastradas"""
        df = self.db.read_sql(
            """
            SELECT DISTINCT superintendencia 
            FROM estrutura_organizacional 
            WHERE ativo = 1 
            ORDER BY superintendencia
            """
        )
        if df.empty:
            return []
        return [str(x) for x in df["superintendencia"].dropna().tolist()]
    
    def obter_setores_por_superintendencia(self, superintendencia: str) -> List[str]:
        """Obtém setores de uma superintendência"""
        df = self.db.read_sql(
            """
            SELECT setor 
            FROM estrutura_organizacional 
            WHERE superintendencia = ? AND ativo = 1
            ORDER BY setor
            """,
            (superintendencia,)
        )
        if df.empty:
            return []
        return [str(x) for x in df["setor"].dropna().tolist()]
    
    def obter_local_fisico_por_setor(self, setor: str) -> Optional[str]:
        """Obtém o local físico de um setor"""
        row = self.db.fetchone(
            """
            SELECT local_fisico 
            FROM estrutura_organizacional 
            WHERE setor = ? AND ativo = 1
            """,
            (setor,)
        )
        return str(row["local_fisico"]) if row and row["local_fisico"] else None
    
    def obter_sigla_superintendencia(self, superintendencia: str) -> Optional[str]:
        """Obtém a sigla de uma superintendência"""
        row = self.db.fetchone(
            """
            SELECT sigla_superintendencia 
            FROM estrutura_organizacional 
            WHERE superintendencia = ? AND ativo = 1
            LIMIT 1
            """,
            (superintendencia,)
        )
        return str(row["sigla_superintendencia"]) if row else None
    
    def obter_codigo_setor(self, setor: str) -> Optional[str]:
        """Obtém o código de um setor"""
        row = self.db.fetchone(
            """
            SELECT codigo 
            FROM estrutura_organizacional 
            WHERE setor = ? AND ativo = 1
            """,
            (setor,)
        )
        return str(row["codigo"]) if row else None
    
    def buscar_setores(self, termo: str, limit: int = 20) -> pd.DataFrame:
        """Busca setores por nome"""
        termo = f"%{termo}%"
        return self.db.read_sql(
            """
            SELECT * FROM estrutura_organizacional 
            WHERE setor LIKE ? OR superintendencia LIKE ? OR sigla_superintendencia LIKE ?
            ORDER BY superintendencia, setor
            LIMIT ?
            """,
            (termo, termo, termo, limit)
        )
    
    def get_estatisticas(self) -> Dict[str, Any]:
        """Retorna estatísticas da estrutura organizacional"""
        total_super = self.db.fetchone("SELECT COUNT(DISTINCT superintendencia) as c FROM estrutura_organizacional WHERE ativo = 1")
        total_setores = self.db.fetchone("SELECT COUNT(*) as c FROM estrutura_organizacional WHERE ativo = 1")
        locais_fisicos = self.db.fetchone("SELECT COUNT(DISTINCT local_fisico) as c FROM estrutura_organizacional WHERE local_fisico IS NOT NULL AND local_fisico != ''")
        
        return {
            "total_superintendencias": int(total_super["c"]) if total_super else 0,
            "total_setores": int(total_setores["c"]) if total_setores else 0,
            "total_locais_fisicos": int(locais_fisicos["c"]) if locais_fisicos else 0
        }