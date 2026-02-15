"""
conftest.py - Configuração de fixtures para testes
"""

import os
import pytest
import tempfile
import sqlite3
from datetime import date

from core.database import Database
from core.security import Security
from core.auth_service import AuditLog, Auth  # CORRIGIDO: import específico
from core.servidor_service import ServidoresService  # CORRIGIDO: import específico
from core.vacinacao_service import VacinacaoService  # CORRIGIDO: import específico
from core.campanha_service import CampanhasService  # CORRIGIDO: import específico
from core.relatorio_service import RelatoriosService  # CORRIGIDO: import específico
from core.estrutura_service import EstruturaOrganizacionalService  # CORRIGIDO: import específico


@pytest.fixture
def temp_db_path():
    """Cria um arquivo de banco de dados temporário"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def db(temp_db_path):
    """Cria uma instância do banco de dados com schema inicializado"""
    db = Database(temp_db_path)
    db.init_schema()
    db.ensure_seed_data()
    return db


@pytest.fixture
def audit(db):
    """Cria instância do AuditLog"""
    return AuditLog(db)


@pytest.fixture
def auth(db):
    """Cria instância do Auth"""
    return Auth(db)


@pytest.fixture
def servidores_service(db, audit):
    """Cria instância do ServidoresService"""
    return ServidoresService(db, audit)


@pytest.fixture
def vacinacao_service(db, audit):
    """Cria instância do VacinacaoService"""
    return VacinacaoService(db, audit)


@pytest.fixture
def campanhas_service(db, audit):
    """Cria instância do CampanhasService"""
    return CampanhasService(db, audit)


@pytest.fixture
def relatorios_service(db):
    """Cria instância do RelatoriosService"""
    return RelatoriosService(db)


@pytest.fixture
def estrutura_service(db, audit):
    """Cria instância do EstruturaOrganizacionalService"""
    return EstruturaOrganizacionalService(db, audit)


@pytest.fixture
def sample_servidor_data():
    """Dados de exemplo para servidor"""
    return {
        "numfunc": "12345",
        "numvinc": "1",
        "nome": "MARIA DA SILVA SANTOS",
        "cpf": "12345678909",  # CPF válido para teste
        "data_nascimento": date(1980, 5, 15),
        "sexo": "FEMININO",
        "cargo": "ANALISTA",
        "lotacao": "RECURSOS HUMANOS",
        "lotacao_fisica": "ANEXO 1",
        "superintendencia": "SUP GESTÃO ADMINISTRATIVA",
        "telefone": "(11) 99999-9999",
        "email": "maria.silva@exemplo.com",
        "data_admissao": date(2010, 3, 10),
        "tipo_vinculo": "EFETIVO",
        "situacao_funcional": "ATIVO"
    }


@pytest.fixture
def sample_vacinacao_data():
    """Dados de exemplo para vacinação"""
    return {
        "vacina": "Influenza",
        "dose": "Anual",
        "data_ap": date.today(),
        "data_ret": date.today().replace(year=date.today().year + 1),
        "lote": "LOT12345",
        "fabricante": "Butantan",
        "local_aplicacao": "NASST Central",
        "via_aplicacao": "Intramuscular"
    }


@pytest.fixture
def sample_campanha_data():
    """Dados de exemplo para campanha"""
    return {
        "nome": "Campanha de Influenza 2024",
        "vacina": "Influenza",
        "publico_alvo": ["Todos os servidores"],
        "data_inicio": date(2024, 4, 1),
        "data_fim": date(2024, 5, 31),
        "status": "PLANEJADA",
        "descricao": "Campanha anual de vacinação contra Influenza"
    }