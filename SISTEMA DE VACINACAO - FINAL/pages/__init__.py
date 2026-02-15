# pages/__init__.py
from .login import LoginPage
from .dashboard import DashboardPage
from .vacinacao import VacinacaoPage
from .servidores import ServidoresPage
from .campanhas import CampanhasPage
from .relatorios import RelatoriosPage
from .relatorios_avancados import RelatoriosAvancadosPage
from .produtividade import ProdutividadePage
from .alterar_senha import AlterarSenhaPage
from .logs import LogsPage
from .admin import AdminPage
from .estrutura import EstruturaPage
from .gerenciar_vacinacoes import GerenciarVacinacoesPage  # NOVO

__all__ = [
    'LoginPage',
    'DashboardPage',
    'VacinacaoPage',
    'ServidoresPage',
    'CampanhasPage',
    'RelatoriosPage',
    'RelatoriosAvancadosPage',
    'ProdutividadePage',
    'AlterarSenhaPage',
    'LogsPage',
    'AdminPage',
    'EstruturaPage',
    'GerenciarVacinacoesPage',  # NOVO
]