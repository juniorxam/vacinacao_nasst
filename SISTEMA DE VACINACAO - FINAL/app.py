"""
app.py - NASST Digital v1.1
Ponto de entrada principal da aplicação Streamlit
"""

import streamlit as st
import os
import sys
import atexit
from datetime import datetime

# Configuração da página DEVE ser a primeira chamada Streamlit
st.set_page_config(
    page_title="NASST Digital - Controle de Vacinação",
    page_icon="💉",  # ✅ Mudei de 📈 para 💉
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Configurar logging ANTES de qualquer outra coisa
from core.logger import setup_logging, get_logger
logger = setup_logging()
logger.info("=" * 60)
logger.info("NASST Digital iniciando - v1.1")
logger.info("=" * 60)

# CSS para esconder navegação padrão
st.markdown("""
<style>
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stSidebar"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports da aplicação
from config import CONFIG
from core.database import OptimizedDatabase
from core.security import Security, Formatters
from core.auth_service import AuditLog, Auth
from core.servidor_service import ServidoresService
from core.vacinacao_service import VacinacaoService
from core.campanha_service import CampanhasService
from core.relatorio_service import RelatoriosService, RelatoriosGerenciaisService
from core.estrutura_service import EstruturaOrganizacionalService
from core.whatsapp_service import NotificacaoCampanhaService
from ui.styles import Styles
from ui.components import UIComponents
from ui.accessibility import AccessibilityManager
from core.backup import BackupManager, BackupScheduler

# Imports das páginas
import importlib.util

pages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")

def load_page_class(filename, class_name):
    """Carrega uma classe de página dinamicamente dos arquivos .py"""
    try:
        filepath = os.path.join(pages_dir, filename)
        spec = importlib.util.spec_from_file_location(filename[:-3], filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[filename[:-3]] = module
        spec.loader.exec_module(module)
        logger.debug(f"Página carregada: {filename}")
        return getattr(module, class_name)
    except Exception as e:
        logger.error(f"Erro ao carregar página {filename}: {e}", exc_info=True)
        raise

# Carrega todas as páginas
LoginPage = load_page_class("login.py", "LoginPage")
DashboardPage = load_page_class("dashboard.py", "DashboardPage")
VacinacaoPage = load_page_class("vacinacao.py", "VacinacaoPage")
ServidoresPage = load_page_class("servidores.py", "ServidoresPage")
CampanhasPage = load_page_class("campanhas.py", "CampanhasPage")
RelatoriosPage = load_page_class("relatorios.py", "RelatoriosPage")
RelatoriosAvancadosPage = load_page_class("relatorios_avancados.py", "RelatoriosAvancadosPage")
ProdutividadePage = load_page_class("produtividade.py", "ProdutividadePage")
AlterarSenhaPage = load_page_class("alterar_senha.py", "AlterarSenhaPage")
LogsPage = load_page_class("logs.py", "LogsPage")
AdminPage = load_page_class("admin.py", "AdminPage")
EstruturaPage = load_page_class("estrutura.py", "EstruturaPage")
GerenciarVacinacoesPage = load_page_class("gerenciar_vacinacoes.py", "GerenciarVacinacoesPage")
NotificacoesPage = load_page_class("notificacoes.py", "NotificacoesPage")


class NASSTApp:
    """
    Classe principal da aplicação NASST Digital.
    Gerencia estado, serviços, navegação e injeção de dependências.
    """
    
    def __init__(self):
        self.db = None
        self.auth = None
        self.audit = None
        self.servidores = None
        self.vacinacao = None
        self.campanhas = None
        self.relatorios = None
        self.relatorios_gerenciais = None
        self.estrutura = None
        self.whatsapp = None
        self.backup_manager = None
        
        logger.info("Inicializando aplicação NASST")
        
        # Inicializa serviços
        self._init_services()
        
        # Inicializa backup automático
        self._init_backup()
        
        # Inicializa estado da sessão
        self._init_session_state()
        
        # Registrar shutdown hook
        atexit.register(self._shutdown)
        
        logger.info("Aplicação inicializada com sucesso")
    
    def _init_services(self):
        """Inicializa todos os serviços com injeção de dependências"""
        try:
            logger.info(f"Conectando ao banco de dados: {CONFIG.db_path_v7}")
            
            # Database
            self.db = OptimizedDatabase(CONFIG.db_path_v7)
            
            # Garante schema e dados iniciais
            self.db.init_schema()
            self.db.ensure_seed_data()
            self.db.maybe_migrate_from_v6()
            
            # Serviços core
            self.audit = AuditLog(self.db)
            self.auth = Auth(self.db)
            
            # Serviços de negócio
            self.servidores = ServidoresService(self.db, self.audit)
            self.vacinacao = VacinacaoService(self.db, self.audit)
            self.campanhas = CampanhasService(self.db, self.audit)
            self.relatorios = RelatoriosService(self.db)
            self.relatorios_gerenciais = RelatoriosGerenciaisService(self.db)
            self.estrutura = EstruturaOrganizacionalService(self.db, self.audit)
            self.whatsapp = NotificacaoCampanhaService(self.db)
            
            logger.info("Serviços inicializados com sucesso")
            
        except Exception as e:
            logger.critical(f"Erro ao inicializar serviços: {e}", exc_info=True)
            st.error(f"❌ Erro ao inicializar serviços: {str(e)}")
            st.stop()
    
    def _init_backup(self):
        """Inicializa o sistema de backup automático"""
        try:
            # Criar diretório de backups se não existir
            os.makedirs("backups", exist_ok=True)
            
            # Inicializar gerenciador de backup
            self.backup_manager = BackupManager(CONFIG.db_path_v7, "backups")
            
            # Carregar configurações de agendamento
            scheduler = BackupScheduler(self.backup_manager)
            schedule_config = scheduler.load_schedule()
            
            # Iniciar backup automático se estiver configurado
            if schedule_config.get("enabled", False):
                interval = schedule_config.get("interval", 24)
                self.backup_manager.start_auto_backup(
                    interval_hours=interval,
                    callback=self._on_backup_completed
                )
                logger.info(f"Backup automático iniciado: {interval}h")
                
                # Registrar no log de auditoria
                if hasattr(self, 'audit') and self.audit:
                    self.audit.registrar(
                        "SISTEMA",
                        "BACKUP",
                        "Backup automático iniciado",
                        f"Intervalo: {interval} horas",
                        "127.0.0.1"
                    )
        
        except Exception as e:
            logger.error(f"Erro ao inicializar backup automático: {e}")
    
    def _on_backup_completed(self, backup_path):
        """Callback executado quando um backup automático é concluído"""
        try:
            logger.info(f"Backup automático concluído: {backup_path}")
            
            if hasattr(self, 'audit') and self.audit:
                self.audit.registrar(
                    "SISTEMA",
                    "BACKUP",
                    "Backup automático concluído",
                    f"Arquivo: {os.path.basename(backup_path)}",
                    "127.0.0.1"
                )
        except Exception as e:
            logger.error(f"Erro no callback de backup: {e}")
    
    def _shutdown(self):
        """Finaliza a aplicação de forma segura"""
        logger.info("Encerrando aplicação NASST")
        
        if self.backup_manager:
            self.backup_manager.stop_auto_backup()
            logger.info("Backup automático parado")
            
            if hasattr(self, 'audit') and self.audit:
                self.audit.registrar(
                    "SISTEMA",
                    "BACKUP",
                    "Backup automático encerrado",
                    "Aplicação finalizada",
                    "127.0.0.1"
                )
    
    def _init_session_state(self):
        """Inicializa variáveis de estado da sessão"""
        defaults = {
            "logado": False,
            "usuario_login": "",
            "usuario_nome": "",
            "nivel_acesso": "VISUALIZADOR",
            "pagina_atual": "login",
            "ultima_busca": "",
            "servidores_filtrados": None,
            "relatorio_avancado": None,
            "servidores_massa": None,
            "dados_vacinacao_processados": None,
            "vacinacao_submit_lock": False,
            "page_gerenciar": 1,
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
        
        logger.debug(f"Sessão inicializada para {len(defaults)} variáveis")
    
    def _inject_styles(self):
        """Injeta CSS e JavaScript personalizado"""
        try:
            Styles.inject()
            AccessibilityManager.inject_accessibility_js()
        except Exception as e:
            logger.warning(f"Erro ao injetar estilos: {e}")
    
    def _render_sidebar(self):
        """Renderiza menu lateral de navegação apenas para usuários logados"""
        if not st.session_state.get('logado', False):
            return
        
        # CSS para mostrar a sidebar apenas quando logado
        st.markdown("""
        <style>
            [data-testid="stSidebar"] { display: block !important; }
        </style>
        """, unsafe_allow_html=True)
        
        with st.sidebar:
            AccessibilityManager.create_high_contrast_toggle()
            st.markdown("---")
            
            st.markdown("### 📍 Menu")
            
            menu_items = [
                ("🏠 Dashboard", "dashboard"),
                ("💉 Vacinação", "vacinacao"),
                ("👥 Servidores", "servidores"),
                ("📅 Campanhas", "campanhas"),
                ("📋 Relatórios", "relatorios"),
            ]
            
            if st.session_state.get('nivel_acesso') in ["ADMIN", "OPERADOR"]:
                menu_items.extend([
                    ("📋 Gerenciar Vacinações", "gerenciar_vacinacoes"),
                    ("📱 Notificações WhatsApp", "notificacoes"),
                    ("📈 Relatórios Avançados", "relatorios_avancados"),
                    ("📊 Produtividade", "produtividade"),
                ])
            
            if st.session_state.get('nivel_acesso') == "ADMIN":
                menu_items.extend([
                    ("🏢 Estrutura", "estrutura"),
                    ("📝 Logs", "logs"),
                    ("⚙️ Administração", "admin"),
                ])
            
            for label, page in menu_items:
                current_page = st.session_state.get('pagina_atual', 'login')
                btn_type = "primary" if current_page == page else "secondary"
                
                if st.button(label, use_container_width=True, type=btn_type, key=f"nav_{page}"):
                    logger.debug(f"Navegação: {page}")
                    st.session_state.pagina_atual = page
                    st.rerun()
            
            st.markdown("---")
            st.markdown(f"**👤 {st.session_state.get('usuario_nome', 'Usuário')}**")
            st.markdown(f"🔑 {st.session_state.get('nivel_acesso', 'VISUALIZADOR')}")
            
            if st.button("🔐 Alterar Minha Senha", use_container_width=True, type="secondary", key="btn_alterar_senha"):
                st.session_state.pagina_atual = "alterar_senha"
                st.rerun()

            if st.button("🚪 Sair", use_container_width=True, type="secondary"):
                self._logout()
    
    def _logout(self):
        """Realiza logout do usuário"""
        usuario = st.session_state.get('usuario_nome', '')
        logger.info(f"Logout do usuário: {usuario}")
        
        # Registra no audit
        if usuario and hasattr(self, 'audit') and self.audit:
            try:
                self.audit.registrar(
                    usuario,
                    "AUTH",
                    "Logout",
                    "Usuário desconectou do sistema",
                    "127.0.0.1"
                )
            except Exception as e:
                logger.error(f"Erro ao registrar logout: {e}")
        
        # Limpa estado
        keys_to_clear = [
            "logado", "usuario_login", "usuario_nome", "nivel_acesso", 
            "pagina_atual", "ultima_busca", "servidores_filtrados",
            "relatorio_avancado", "servidores_massa", 
            "dados_vacinacao_processados", "page_gerenciar",
            "dose_excluir", "usuario_excluir", "registros_vacinacao"
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        st.session_state.pagina_atual = "login"
        st.rerun()
    
    def _route_page(self):
        """Roteia para a página atual"""
        page = st.session_state.get('pagina_atual', 'login')
        
        # TELA DE LOGIN (pública)
        if page == "login" or not st.session_state.get('logado', False):
            st.markdown("""
            <style>
                [data-testid="stSidebar"] {display: none !important;}
                section[data-testid="stSidebar"] {display: none !important;}
                .css-1cypcdb {display: none !important;}
            </style>
            """, unsafe_allow_html=True)
            
            login_page = LoginPage(self.auth, self.audit)
            login_page.render()
            return
        
        # PÁGINAS INTERNAS
        if not st.session_state.get('logado', False):
            st.session_state.pagina_atual = "login"
            st.rerun()
            return
        
        # Roteamento
        pages_map = {
            "dashboard": lambda: DashboardPage(
                self.db, self.relatorios, self.servidores, 
                self.vacinacao, self.relatorios_gerenciais
            ),
            "vacinacao": lambda: VacinacaoPage(
                self.db, self.vacinacao, self.servidores, 
                self.campanhas, self.auth
            ),
            "servidores": lambda: ServidoresPage(
                self.db, self.servidores, self.auth, self.estrutura
            ),
            "campanhas": lambda: CampanhasPage(
                self.db, self.campanhas, self.vacinacao, 
                self.auth, self.relatorios_gerenciais
            ),
            "relatorios": lambda: RelatoriosPage(
                self.db, self.relatorios, self.relatorios_gerenciais, self.servidores
            ),
            "relatorios_avancados": lambda: RelatoriosAvancadosPage(
                self.db, self.relatorios, self.auth
            ),
            "produtividade": lambda: ProdutividadePage(
                self.db, self.auth
            ),
            "alterar_senha": lambda: AlterarSenhaPage(
                self.db, self.auth, self.audit
            ),
            "logs": lambda: LogsPage(self.db, self.auth),
            "admin": lambda: AdminPage(self.db, self.auth, self.servidores),
            "estrutura": lambda: EstruturaPage(self.db, self.auth, self.estrutura),
            "gerenciar_vacinacoes": lambda: GerenciarVacinacoesPage(
                self.db, self.vacinacao, self.auth, self.audit
            ),
            "notificacoes": lambda: NotificacoesPage(
                self.db, self.auth, self.audit
            ),
        }
        
        if page in pages_map:
            try:
                logger.debug(f"Renderizando página: {page}")
                page_instance = pages_map[page]()
                page_instance.render()
            except Exception as e:
                logger.error(f"Erro ao renderizar página {page}: {e}", exc_info=True)
                st.error(f"❌ Erro ao carregar página '{page}': {str(e)}")
                if st.session_state.get('nivel_acesso') == "ADMIN" and CONFIG.debug:
                    st.exception(e)
                st.info("Tente fazer login novamente ou contate o administrador.")
        else:
            logger.error(f"Página não encontrada: {page}")
            st.error(f"❌ Página '{page}' não encontrada")
            st.session_state.pagina_atual = "dashboard"
            st.rerun()
    
    def run(self):
        """Método principal de execução da aplicação"""
        self._inject_styles()
        self._render_sidebar()
        self._route_page()


def main():
    """Função de entrada principal"""
    try:
        app = NASSTApp()
        app.run()
    except Exception as e:
        logger = get_logger(__name__)
        logger.critical(f"Erro fatal na aplicação: {e}", exc_info=True)
        st.error(f"❌ Erro crítico na aplicação: {str(e)}")
        if CONFIG.debug:
            st.exception(e)


if __name__ == "__main__":
    main()
