"""
dashboard.py - Página do painel de controle
"""

from datetime import date

import plotly.express as px
import streamlit as st
from dateutil.relativedelta import relativedelta

from config import CONFIG
from core.security import Security, Formatters
from core.relatorio_service import RelatorioPDFService
from ui.components import UIComponents


class DashboardPage:
    """Página do dashboard"""
    
    def __init__(self, db, relatorios, servidores, vacinacao, relatorios_gerenciais):
        self.db = db
        self.relatorios = relatorios
        self.servidores = servidores
        self.vacinacao = vacinacao
        self.relatorios_gerenciais = relatorios_gerenciais
    
    def render(self):
        """Renderiza o dashboard"""
        st.markdown('<div id="main-content"></div>', unsafe_allow_html=True)
        st.title("📊 Painel de Controle - NASST Digital")
        UIComponents.breadcrumb("🏠 Início", "Dashboard")

        with UIComponents.show_loading_indicator("Carregando métricas..."):
            m = self.relatorios.get_metricas_gerais()
            
            # Buscar número de servidores vacinados
            vacinados = self.db.fetchone("SELECT COUNT(DISTINCT id_comp) as total FROM doses")
            total_vacinados = vacinados['total'] if vacinados else 0

        # Cards de métricas
        col1, col2, col3, col4 = st.columns(4)

        metric_cards = [
            ("👥 Servidores Ativos", m["total_servidores"], "#3b82f6"),
            ("💉 Total de Doses", m["total_doses"], "#10b981"),
            ("✅ Servidores Vacinados", f"{total_vacinados}", "#8b5cf6"),
            ("📊 Cobertura", f"{m['cobertura']:.1f}%", "#f59e0b"),
        ]

        for col, (title, value, color) in zip([col1, col2, col3, col4], metric_cards):
            with col:
                st.markdown(
                    f"""
                    <div style="
                        background: {color}10;
                        border: 2px solid {color};
                        border-radius: 12px;
                        padding: 20px;
                        text-align: center;
                        margin-bottom: 16px;
                        height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                    ">
                        <div style="font-size: 32px; margin-bottom: 4px;">{title.split()[0]}</div>
                        <div style="font-size: 32px; font-weight: 700; color: {color};">{value}</div>
                        <div style="font-size: 14px; color: #6b7280; margin-top: 4px;">{title}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # ===== GRÁFICOS POR SUPERINTENDÊNCIA =====
        st.subheader("🏢 Análise por Superintendência")
        
        with UIComponents.show_loading_indicator("Carregando dados por superintendência..."):
            # Query para buscar dados por superintendência
            df_super = self.db.read_sql("""
                SELECT 
                    s.superintendencia,
                    COUNT(DISTINCT s.id_comp) as total_servidores,
                    COUNT(DISTINCT d.id_comp) as servidores_vacinados
                FROM servidores s
                LEFT JOIN doses d ON s.id_comp = d.id_comp
                WHERE s.situacao_funcional = 'ATIVO'
                  AND s.superintendencia IS NOT NULL
                  AND s.superintendencia != ''
                GROUP BY s.superintendencia
                HAVING total_servidores > 0
                ORDER BY servidores_vacinados DESC
            """)
            
            if not df_super.empty:
                # Calcular percentual de cobertura
                df_super['percentual'] = (df_super['servidores_vacinados'] / df_super['total_servidores'] * 100).round(1)
                
                # Criar duas colunas para os gráficos lado a lado
                col_graf1, col_graf2 = st.columns(2)
                
                with col_graf1:
                    # GRÁFICO 1: Valores Absolutos
                    fig_absoluto = px.bar(
                        df_super.head(10),
                        x='superintendencia',
                        y='servidores_vacinados',
                        title='Top 10 - Servidores Vacinados (Valores Absolutos)',
                        labels={
                            'superintendencia': 'Superintendência', 
                            'servidores_vacinados': 'Número de Servidores Vacinados'
                        },
                        color='servidores_vacinados',
                        color_continuous_scale='blues',
                        text='servidores_vacinados'
                    )
                    
                    fig_absoluto.update_traces(
                        textposition='outside',
                        textfont_size=10
                    )
                    
                    fig_absoluto.update_layout(
                        height=400,
                        xaxis_tickangle=-45,
                        showlegend=False,
                        coloraxis_showscale=False,
                        margin=dict(l=50, r=20, t=50, b=100)
                    )
                    
                    st.plotly_chart(fig_absoluto, use_container_width=True)
                
                with col_graf2:
                    # GRÁFICO 2: Percentuais
                    # Ordenar por percentual para o gráfico
                    df_percentual = df_super.sort_values('percentual', ascending=False).head(10)
                    
                    fig_percentual = px.bar(
                        df_percentual,
                        x='superintendencia',
                        y='percentual',
                        title='Top 10 - Cobertura Vacinal (%)',
                        labels={
                            'superintendencia': 'Superintendência', 
                            'percentual': 'Cobertura (%)'
                        },
                        color='percentual',
                        color_continuous_scale='greens',
                        text='percentual',
                        range_y=[0, 100]
                    )
                    
                    fig_percentual.update_traces(
                        textposition='outside',
                        textfont_size=10,
                        texttemplate='%{text}%'
                    )
                    
                    # Adicionar linha da meta (80%)
                    fig_percentual.add_hline(
                        y=80, 
                        line_dash="dash", 
                        line_color="red",
                        annotation_text="Meta 80%",
                        annotation_position="top right"
                    )
                    
                    fig_percentual.update_layout(
                        height=400,
                        xaxis_tickangle=-45,
                        showlegend=False,
                        coloraxis_showscale=False,
                        margin=dict(l=50, r=20, t=50, b=100)
                    )
                    
                    st.plotly_chart(fig_percentual, use_container_width=True)
                
                # Mostrar tabela completa
                with st.expander("📋 Ver tabela completa por superintendência"):
                    df_display = df_super.copy()
                    df_display['percentual'] = df_display['percentual'].astype(str) + '%'
                    df_display = df_display.sort_values('servidores_vacinados', ascending=False)
                    
                    st.dataframe(
                        df_display,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "superintendencia": "Superintendência",
                            "total_servidores": "Total de Servidores",
                            "servidores_vacinados": "Servidores Vacinados",
                            "percentual": "Cobertura"
                        }
                    )
                    
                    # Estatísticas adicionais
                    col_est1, col_est2, col_est3 = st.columns(3)
                    
                    with col_est1:
                        acima_meta = len(df_super[df_super['percentual'] >= 80])
                        st.metric("Superintendências acima da meta (80%)", acima_meta)
                    
                    with col_est2:
                        media_geral = df_super['percentual'].mean()
                        st.metric("Média de cobertura", f"{media_geral:.1f}%")
                    
                    with col_est3:
                        melhor = df_super.loc[df_super['percentual'].idxmax()]
                        st.metric("Melhor cobertura", f"{melhor['superintendencia']} ({melhor['percentual']:.1f}%)")
            else:
                st.info("Não há dados suficientes para gerar os gráficos por superintendência.")
        
        st.markdown("---")
        
        # Abas de gráficos
        tab1, tab2 = st.tabs(["📈 Cobertura por Lotação", "📅 Distribuição Mensal"])

        with tab1:
            with UIComponents.show_loading_indicator("Gerando gráfico..."):
                fig = self.relatorios.grafico_cobertura_lotacao_top10()
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Não há dados suficientes para gerar o gráfico de cobertura por lotação.")

        with tab2:
            with UIComponents.show_loading_indicator("Carregando dados..."):
                df_m = self.relatorios.doses_ultimos_6_meses()
                if not df_m.empty:
                    fig_m = px.bar(
                        df_m,
                        x="mes",
                        y="total_doses",
                        color="vacina",
                        title="Doses Aplicadas nos Últimos 6 Meses",
                        labels={"mes": "Mês", "total_doses": "Total de Doses", "vacina": "Vacina"},
                        height=400,
                        barmode="group"
                    )
                    st.plotly_chart(fig_m, use_container_width=True)
                else:
                    st.info("Não há registros de vacinação nos últimos 6 meses.")

        # Estatísticas rápidas
        st.subheader("📊 Estatísticas Rápidas")
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        with col_stat1:
            total_servidores = self.db.fetchone("SELECT COUNT(*) as total FROM servidores WHERE situacao_funcional = 'ATIVO'")
            st.metric("Servidores Ativos", f"{total_servidores['total'] if total_servidores else 0:,}")
        
        with col_stat2:
            total_vacinas = self.db.fetchone("SELECT COUNT(DISTINCT vacina) as total FROM doses")
            st.metric("Vacinas Diferentes", f"{total_vacinas['total'] if total_vacinas else 0}")
        
        with col_stat3:
            total_servidores_ativos = total_servidores['total'] if total_servidores else 1
            percentual = (total_vacinados / total_servidores_ativos * 100) if total_servidores_ativos > 0 else 0
            st.metric("Taxa de Vacinados", f"{percentual:.1f}%")
        
        with col_stat4:
            if total_vacinados > 0:
                total_doses = m["total_doses"]
                media = total_doses / total_vacinados
                st.metric("Média de Doses", f"{media:.1f}")
            else:
                st.metric("Média de Doses", "0")

        # Consulta rápida
        with st.expander("🔍 Consulta Rápida de Servidores", expanded=False):
            col_search1, col_search2 = st.columns([3, 1])
            
            with col_search1:
                search_term = st.text_input(
                    "Digite nome, CPF ou matrícula:",
                    key="quick_search",
                    placeholder="Pressione F para focar aqui...",
                    help="Comece a digitar para buscar automaticamente"
                )
            
            with col_search2:
                st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
                buscar = st.button("🔍 Buscar", key="btn_quick_search", use_container_width=True)

            if search_term or buscar:
                with UIComponents.show_loading_indicator("Buscando..."):
                    servidores = self.servidores.buscar_servidores(search_term, limit=20)

                    if not servidores.empty:
                        st.success(f"✅ {len(servidores)} servidores encontrados")
                        
                        tab_res1, tab_res2 = st.tabs(["📋 Lista", "📊 Detalhes"])
                        
                        with tab_res1:
                            df_display = servidores[['nome', 'cpf', 'lotacao', 'cargo', 'situacao_funcional']].copy()
                            df_display['cpf'] = df_display['cpf'].apply(lambda x: Security.formatar_cpf(x) if pd.notna(x) else '')
                            df_display = df_display.rename(columns={
                                'nome': 'Nome',
                                'cpf': 'CPF',
                                'lotacao': 'Lotação',
                                'cargo': 'Cargo',
                                'situacao_funcional': 'Situação'
                            })
                            st.dataframe(df_display, use_container_width=True, hide_index=True)
                        
                        with tab_res2:
                            for _, s in servidores.iterrows():
                                with st.container():
                                    st.markdown(f"### 👤 {s['nome']}")
                                    col_info1, col_info2, col_info3 = st.columns(3)
                                    
                                    with col_info1:
                                        st.markdown(f"**📋 CPF:** {Security.formatar_cpf(s['cpf'])}")
                                        st.markdown(f"**📍 Lotação:** {s['lotacao']}")
                                    
                                    with col_info2:
                                        st.markdown(f"**🏢 Superintendência:** {s.get('superintendencia', 'N/I')}")
                                        st.markdown(f"**💼 Cargo:** {s.get('cargo', 'N/I')}")
                                    
                                    with col_info3:
                                        st.markdown(f"**📝 Matrícula:** {s['numfunc']}-{s['numvinc']}")
                                        st.markdown(f"**📊 Situação:** {s['situacao_funcional']}")
                                    
                                    if st.button(f"📋 Ver Histórico Completo", key=f"hist_{s['id_comp']}"):
                                        st.session_state.consulta_servidor = s['id_comp']
                                        st.session_state.pagina_atual = "relatorios"
                                        st.rerun()
                                    
                                    st.markdown("---")
                    else:
                        st.info("Nenhum servidor encontrado com os critérios de busca.")