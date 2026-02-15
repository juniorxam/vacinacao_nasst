"""
styles.py - Estilos CSS personalizados
"""

import streamlit as st


class Styles:
    """Classe para gerenciar estilos CSS da aplicação"""
    
    @staticmethod
    def inject():
        """Injeta CSS personalizado na aplicação"""
        st.markdown("""
        <style>
        /* ===== REDUÇÃO DE ESPAÇAMENTO GLOBAL ===== */
        
        /* Reduzir padding do container principal */
        .main .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 100% !important;
        }
        
        /* Reduzir margem dos títulos */
        h1 {
            margin-top: 0.25rem !important;
            margin-bottom: 0.25rem !important;
            padding-top: 0 !important;
            font-size: 2rem !important;
        }
        
        h2 {
            margin-top: 0.25rem !important;
            margin-bottom: 0.25rem !important;
            font-size: 1.5rem !important;
        }
        
        h3 {
            margin-top: 0.15rem !important;
            margin-bottom: 0.15rem !important;
        }
        
        /* Reduzir espaçamento de todos os elementos */
        .stAlert, .stSuccess, .stError, .stWarning, .stInfo {
            margin-top: 0.25rem !important;
            margin-bottom: 0.25rem !important;
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
        }
        
        /* Reduzir espaçamento de colunas */
        .row-widget {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
        }
        
        .element-container {
            margin-bottom: 0.1rem !important;
        }
        
        /* Reduzir espaçamento de abas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem !important;
            margin-bottom: 0.25rem !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding-top: 0.25rem !important;
            padding-bottom: 0.25rem !important;
        }
        
        /* Reduzir espaçamento de botões */
        .stButton button {
            margin-top: 0 !important;
            margin-bottom: 0.1rem !important;
        }
        
        /* Reduzir espaçamento de inputs */
        .stTextInput, .stSelectbox, .stDateInput, .stNumberInput {
            margin-bottom: 0.25rem !important;
        }
        
        /* Reduzir espaçamento de métricas */
        .stMetric {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        
        .stMetric label {
            margin-top: 0 !important;
        }
        
        .stMetric [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
        }
        
        /* Reduzir espaçamento de expanders */
        .streamlit-expanderHeader {
            padding-top: 0.25rem !important;
            padding-bottom: 0.25rem !important;
        }
        
        /* ===== SIDEBAR (MENU LATERAL) ===== */
        
        /* Reduzir altura da sidebar */
        [data-testid="stSidebar"] {
            padding-top: 0.5rem !important;
            width: 250px !important;
        }
        
        /* Reduzir espaçamento interno da sidebar */
        [data-testid="stSidebar"] > div:first-child {
            padding-top: 0.5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Reduzir margem dos itens do menu */
        [data-testid="stSidebar"] .stButton button {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            padding-top: 0.25rem !important;
            padding-bottom: 0.25rem !important;
            font-size: 0.9rem !important;
        }
        
        /* Reduzir tamanho dos títulos na sidebar */
        [data-testid="stSidebar"] h1 {
            font-size: 1.3rem !important;
            margin-top: 0 !important;
            margin-bottom: 0.25rem !important;
        }
        
        [data-testid="stSidebar"] h2 {
            font-size: 1.1rem !important;
            margin-top: 0.25rem !important;
            margin-bottom: 0.25rem !important;
        }
        
        [data-testid="stSidebar"] h3 {
            font-size: 1rem !important;
            margin-top: 0.15rem !important;
            margin-bottom: 0.15rem !important;
        }
        
        /* Reduzir espaçamento do texto na sidebar */
        [data-testid="stSidebar"] p {
            margin-top: 0.1rem !important;
            margin-bottom: 0.1rem !important;
            font-size: 0.9rem !important;
        }
        
        /* Reduzir espaçamento das linhas divisórias */
        [data-testid="stSidebar"] hr {
            margin-top: 0.3rem !important;
            margin-bottom: 0.3rem !important;
        }
        
        /* ===== TABELAS ===== */
        
        /* Reduzir altura das linhas da tabela */
        .stDataFrame {
            font-size: 0.9rem !important;
        }
        
        .stDataFrame td, .stDataFrame th {
            padding-top: 0.2rem !important;
            padding-bottom: 0.2rem !important;
        }
        
        /* ===== FORMULÁRIOS ===== */
        
        /* Reduzir espaçamento entre campos do formulário */
        div[data-testid="column"] {
            gap: 0.25rem !important;
        }
        
        /* ===== CARDS E CONTAINERS ===== */
        
        /* Reduzir padding de containers com borda */
        div[style*="border"] {
            padding-top: 0.5rem !important;
            padding-bottom: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* ===== RODAPÉ ===== */
        
        /* Ajustar rodapé */
        footer {
            visibility: hidden !important;
        }
        
        /* ===== BREADCRUMB ===== */
        
        /* Ajustar breadcrumb */
        .breadcrumb {
            margin-top: 0.1rem !important;
            margin-bottom: 0.3rem !important;
            padding: 0.2rem 0 !important;
        }
        
        /* Mantém a consistência com o tema claro/escuro */
        @media (prefers-color-scheme: dark) {
            [data-testid="stSidebar"] .stButton button {
                border-color: rgba(250, 250, 250, 0.2);
                color: rgb(250, 250, 250);
            }
            
            [data-testid="stSidebar"] .stButton button:hover {
                background-color: rgba(250, 250, 250, 0.05);
                border-color: rgba(250, 250, 250, 0.3);
            }
            
            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] p {
                color: rgb(250, 250, 250);
            }
        }
        </style>
        """, unsafe_allow_html=True)