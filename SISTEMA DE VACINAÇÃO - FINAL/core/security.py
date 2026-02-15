"""
security.py - Segurança e formatação
"""

import hashlib
import re
import logging
from datetime import date, datetime
from typing import Any, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class Security:
    @staticmethod
    def sha256_hex(value: str) -> str:
        """Gera hash SHA-256 de uma string"""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def clean_cpf(cpf: Any) -> str:
        """Remove caracteres não numéricos do CPF"""
        if cpf is None:
            return ""
        return re.sub(r"[^\d]", "", str(cpf))

    @staticmethod
    def validar_cpf(cpf: Any) -> bool:
        """Valida CPF (algoritmo dos dígitos verificadores)"""
        cpf_str = Security.clean_cpf(cpf)
        
        # Validações básicas
        if len(cpf_str) != 11 or cpf_str == cpf_str[0] * 11:
            logger.debug(f"CPF inválido por tamanho ou dígitos repetidos: {cpf_str}")
            return False

        # Validação do primeiro dígito
        soma = sum(int(cpf_str[i]) * (10 - i) for i in range(9))
        digito1 = (soma * 10) % 11
        if digito1 == 10:
            digito1 = 0

        # Validação do segundo dígito
        soma = sum(int(cpf_str[i]) * (11 - i) for i in range(10))
        digito2 = (soma * 10) % 11
        if digito2 == 10:
            digito2 = 0

        resultado = cpf_str[-2:] == f"{digito1}{digito2}"
        if not resultado:
            logger.debug(f"CPF inválido por dígitos verificadores: {cpf_str}")
        
        return resultado

    @staticmethod
    def formatar_cpf(cpf: Any) -> str:
        """Formata CPF no padrão 000.000.000-00"""
        cpf_str = Security.clean_cpf(cpf)
        if len(cpf_str) == 11:
            return f"{cpf_str[:3]}.{cpf_str[3:6]}.{cpf_str[6:9]}-{cpf_str[9:]}"
        return str(cpf or "")

    @staticmethod
    def safe_select_only(sql: str) -> Tuple[bool, str]:
        """
        Permite somente SELECT em consulta personalizada (admin).
        Bloqueia operações e funções comuns de exfiltração.
        """
        if not sql or not sql.strip():
            return False, "Consulta vazia"
            
        s = sql.strip().lower()
        
        # Deve começar com SELECT
        if not s.startswith("select"):
            logger.warning(f"Consulta bloqueada (não começa com SELECT): {sql[:50]}")
            return False, "Apenas consultas SELECT são permitidas."

        # Palavras bloqueadas
        blocked = [
            "insert", "update", "delete", "drop", "alter", "create",
            "pragma", "attach", "detach", "vacuum", "reindex",
            "replace", "truncate", "exec", "execute", "union",
            "--", "/*", "*/", ";"
        ]
        
        for kw in blocked:
            if re.search(rf'\b{re.escape(kw)}\b', s):
                logger.warning(f"Consulta bloqueada (palavra-chave {kw}): {sql[:50]}")
                return False, f"Comando '{kw}' bloqueado por política de segurança."

        return True, ""


class Formatters:
    @staticmethod
    def parse_date(data_val: Any) -> Optional[date]:
        """Converte diversos formatos para objeto date."""
        if pd.isna(data_val) or data_val is None:
            return None
        
        if isinstance(data_val, date):
            if isinstance(data_val, datetime):
                return data_val.date()
            return data_val
            
        if isinstance(data_val, str):
            data_str = data_val.strip()
            if not data_str:
                return None
            
            # Limpar parte de hora se houver
            if ' ' in data_str:
                data_str = data_str.split(' ')[0]
            
            # Tentar formatos comuns
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    return datetime.strptime(data_str, fmt).date()
                except ValueError:
                    continue
        
        logger.debug(f"Não foi possível converter data: {data_val}")
        return None

    @staticmethod
    def formatar_data_br(data_val: Any) -> str:
        """Formata data para o padrão brasileiro DD/MM/YYYY."""
        dt = Formatters.parse_date(data_val)
        if dt:
            return dt.strftime("%d/%m/%Y")
        return str(data_val) if data_val and not pd.isna(data_val) else ""

    @staticmethod
    def calcular_idade(data_nascimento: Any) -> Optional[int]:
        """Calcula a idade exata em anos."""
        nasc = Formatters.parse_date(data_nascimento)
        if not nasc:
            return None
            
        hoje = date.today()
        try:
            idade = hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
            return idade
        except Exception as e:
            logger.error(f"Erro ao calcular idade: {e}")
            return None

    @staticmethod
    def calcular_tempo_servico(data_admissao: Any) -> str:
        """Calcula tempo de serviço em anos e meses."""
        adm = Formatters.parse_date(data_admissao)
        if not adm:
            return "Não informado"
            
        hoje = date.today()
        anos = hoje.year - adm.year
        meses = hoje.month - adm.month
        if meses < 0:
            anos -= 1
            meses += 12
            
        partes = []
        if anos > 0:
            partes.append(f"{anos} {'ano' if anos == 1 else 'anos'}")
        if meses > 0:
            partes.append(f"{meses} {'mês' if meses == 1 else 'meses'}")
            
        return " e ".join(partes) if partes else "Menos de 1 mês"

    @staticmethod
    def validar_telefone(telefone: Any) -> bool:
        """Valida telefone brasileiro (fixo ou celular)"""
        if not telefone:
            return False
        
        numeros = re.sub(r"[^\d]", "", str(telefone))
        # Aceita 10 (fixo) ou 11 (celular) dígitos
        return len(numeros) in (10, 11)

    @staticmethod
    def validar_email(email: Any) -> bool:
        """Valida formato de email"""
        if not email:
            return False
        
        email_str = str(email).strip().lower()
        # Regex simples para email
        padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(padrao, email_str) is not None