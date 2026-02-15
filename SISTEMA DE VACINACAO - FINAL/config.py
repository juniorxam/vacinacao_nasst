"""
config.py - NASST Digital v1.2
Configurações da aplicação com suporte para Streamlit Cloud
"""

import os
from dataclasses import dataclass
from pathlib import Path

# Detecta se está rodando no Streamlit Cloud
IS_CLOUD = os.getenv('STREAMLIT_RUNTIME_ENV') == 'cloud' or os.getenv('IS_CLOUD') == 'true'

# Define o diretório base (importante para paths relativos)
BASE_DIR = Path(__file__).parent.absolute()


@dataclass(frozen=True)
class AppConfig:
    # Informações da aplicação
    app_title: str = "NASST Digital - Controle de Vacinação"
    page_icon: str = "💉"
    layout: str = "wide"
    initial_sidebar_state: str = "collapsed"

    # Ano exibido
    ano_atual: int = 2026

    # ===== BANCO DE DADOS =====
    # No cloud, usa caminho relativo (dentro do container)
    # Localmente, usa o caminho normal
    db_path_v7: str = str(BASE_DIR / "nasst_sistema_v7.db")
    db_path_v6: str = str(BASE_DIR / "nasst_sistema_v6.db")
    
    # ===== LOGO =====
    # No cloud, o logo deve estar no repositório
    logo_path: str = str(BASE_DIR / "LOGO.png")

    # ===== SEGURANÇA =====
    # Login do admin (pode ser via secrets ou variável de ambiente)
    admin_login: str = os.getenv("ADMIN_LOGIN", "admin")
    
    # SENHA DO ADMIN - PRIORIDADE:
    # 1. Secrets do Streamlit Cloud (via os.getenv)
    # 2. Variável de ambiente local
    # 3. Valor padrão APENAS em desenvolvimento
    admin_password: str = os.getenv("ADMIN_PASSWORD")
    
    # ===== AMBIENTE =====
    # Detecta automaticamente se é produção ou desenvolvimento
    environment: str = os.getenv("ENVIRONMENT", "production" if IS_CLOUD else "development")
    
    # Debug mode (desligado em produção/cloud)
    debug: bool = os.getenv("DEBUG", "False").lower() == "true" and environment == "development"

    # ===== CONFIGURAÇÕES DO STREAMLIT CLOUD =====
    # Baseado em: https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app
    cloud_deployed: bool = IS_CLOUD
    
    # Limite de tamanho de arquivo para upload (em MB)
    # Streamlit Cloud tem limite de 200MB, mas vamos limitar a 10MB por segurança
    max_upload_size_mb: int = 10
    
    # ===== BACKUP =====
    # No cloud, backups são voláteis (não persistem entre deploys)
    # Por isso, desabilitamos ou reduzimos a frequência
    backup_enabled: bool = not IS_CLOUD  # Desabilitado no cloud
    backup_dir: str = str(BASE_DIR / "backups")
    backup_interval_hours: int = 6  # Só usado se backup_enabled = True
    backup_retention_days: int = 15

    # ===== OTIMIZAÇÕES =====
    # Cache TTL (em segundos) - reduzido no cloud para economizar memória
    cache_ttl_seconds: int = 30 if IS_CLOUD else 60


# Instância única da configuração
CONFIG = AppConfig()


# ===== VALIDAÇÕES PÓS-CONFIGURAÇÃO =====

def _validate_config():
    """Valida as configurações e levanta erros se necessário"""
    
    # 1. Validar senha do admin em produção
    if CONFIG.environment == "production" and not CONFIG.admin_password:
        if CONFIG.cloud_deployed:
            raise ValueError(
                "❌ ADMIN_PASSWORD não configurada no Streamlit Cloud!\n\n"
                "Para configurar:\n"
                "1. No seu app no Streamlit Cloud, vá em 'Settings'\n"
                "2. Clique em 'Secrets'\n"
                "3. Adicione: ADMIN_PASSWORD = 'sua_senha_forte_aqui'\n"
                "4. Clique em 'Save'\n"
                "5. Faça um novo deploy"
            )
        else:
            raise ValueError(
                "❌ ADMIN_PASSWORD must be set in production!\n"
                "Use environment variable or .env file."
            )
    
    # 2. Validar diretórios necessários
    if not CONFIG.cloud_deployed:
        # Só cria diretórios localmente
        os.makedirs(CONFIG.backup_dir, exist_ok=True)
        os.makedirs(BASE_DIR / "logs", exist_ok=True)
        os.makedirs(BASE_DIR / "data", exist_ok=True)
    
    # 3. Verificar se o logo existe (warning apenas)
    if not os.path.exists(CONFIG.logo_path):
        print(f"⚠️ Aviso: Arquivo de logo não encontrado em {CONFIG.logo_path}")


# Executa validações
_validate_config()


# ===== FUNÇÕES DE UTILIDADE PARA O CLOUD =====

def get_secret(key: str, default: str = None) -> str:
    """
    Retorna um secret do ambiente (prioriza Streamlit Secrets)
    Útil para acessar outras credenciais no futuro (API keys, etc)
    """
    # Tenta pegar do ambiente (funciona localmente e no cloud)
    value = os.getenv(key, default)
    
    # Se estiver no cloud e não achou, tenta um fallback amigável
    if CONFIG.cloud_deployed and value == default and default is None:
        print(f"⚠️ Secret '{key}' não encontrada no Streamlit Cloud")
    
    return value


def is_cloud() -> bool:
    """Retorna True se estiver rodando no Streamlit Cloud"""
    return CONFIG.cloud_deployed


def get_db_path() -> str:
    """
    Retorna o caminho correto do banco de dados
    Útil se precisar de lógica especial no futuro
    """
    return CONFIG.db_path_v7


# ===== INFO PARA DEBUG =====
if CONFIG.debug:
    print(f"""
    📊 NASST Digital - Configuração
    =================================
    Ambiente: {CONFIG.environment}
    Cloud: {CONFIG.cloud_deployed}
    Banco: {CONFIG.db_path_v7}
    Backup ativo: {CONFIG.backup_enabled}
    Upload máx: {CONFIG.max_upload_size_mb}MB
    =================================
    """)
