"""
relatorios.py - Página de relatórios
"""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st
from dateutil.relativedelta import relativedelta

from config import CONFIG
from core.security import Security, Formatters
from core.relatorio_service import RelatorioPDFService
from ui.components import UIComponents


class RelatoriosPage:
    """Página de relatórios"""
    
    def __init__(self, db, relatorios, relatorios_gerenciais, servidores):
        self.db = db
        self.relatorios = relatorios
        self.relatorios_gerenciais = relatorios_gerenciais
        self.servidores = servidores
    
    def render(self):
        """Renderiza página de relatórios"""
        st.title("📋 Relatórios")
        UIComponents.breadcrumb("🏠 Início", "Relatórios")

        tab1, tab2, tab3 = st.tabs([
            "📊 Cobertura por Lotação", 
            "🏢 Por Superintendência", 
            "👥 Servidores"
        ])

        with tab1:
            self._render_cobertura_geral()
        
        with tab2:
            self._render_superintendencia()
        
        with tab3:
            self._render_servidores()
    
    def _render_cobertura_geral(self):
        """Renderiza relatório de cobertura geral por lotação"""
        st.subheader("📊 Cobertura Vacinal por Lotação")

        col_filt1, col_filt2 = st.columns(2)

        with col_filt1:
            lotacao_filtro = st.selectbox(
                "Lotação:",
                ["TODAS"] + self.servidores.obter_lotacoes(),
                key="rel_lotacao"
            )

        with col_filt2:
            data_ini = st.date_input(
                "Data Inicial:",
                value=date.today() - relativedelta(months=6),
                key="rel_data_ini"
            )
            data_fim = st.date_input(
                "Data Final:",
                value=date.today(),
                key="rel_data_fim"
            )

        if st.button("🔍 Gerar Relatório", use_container_width=True, key="btn_rel_cobertura"):
            with st.spinner("Gerando relatório..."):
                df_cobertura = self.relatorios.cobertura_detalhada(
                    lotacao_filtro,
                    data_ini,
                    data_fim
                )

                if not df_cobertura.empty:
                    st.success(f"✅ Relatório gerado com sucesso!")

                    total_servidores = df_cobertura['total_servidores'].sum()
                    total_vacinados = df_cobertura['total_vacinados'].sum()
                    cobertura_geral = (total_vacinados / total_servidores * 100) if total_servidores > 0 else 0

                    col_met1, col_met2, col_met3 = st.columns(3)

                    with col_met1:
                        st.metric("Total Servidores", f"{total_servidores:,}")

                    with col_met2:
                        st.metric("Servidores Vacinados", f"{total_vacinados:,}")

                    with col_met3:
                        st.metric("Cobertura Geral", f"{cobertura_geral:.1f}%")

                    st.dataframe(
                        df_cobertura,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "lotacao": "Lotação",
                            "total_servidores": "Total Servidores",
                            "vacinados_periodo": "Vacinados (Período)",
                            "total_vacinados": "Total Vacinados",
                            "cobertura_periodo": "Cobertura Período (%)",
                            "cobertura_total": "Cobertura Total (%)"
                        }
                    )

                    fig = px.bar(
                        df_cobertura.head(10),
                        x='lotacao',
                        y=['total_servidores', 'total_vacinados'],
                        title='Cobertura Vacinal por Lotação (Top 10)',
                        barmode='group',
                        labels={'value': 'Quantidade', 'variable': 'Tipo'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    col_exp1, col_exp2 = st.columns(2)

                    with col_exp1:
                        csv = df_cobertura.to_csv(index=False)
                        st.download_button(
                            "📥 CSV",
                            csv,
                            f"cobertura_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                            "text/csv",
                            use_container_width=True
                        )
                else:
                    st.info("📭 Nenhum dado encontrado para os filtros selecionados.")
    
    def _render_superintendencia(self):
        """Renderiza relatório por superintendência"""
        st.subheader("🏢 Relatório por Superintendência")

        col1, col2 = st.columns(2)

        with col1:
            superintendencia_filtro = st.selectbox(
                "Superintendência:",
                ["TODAS"] + self.servidores.obter_superintendencias(),
                key="rel_super_filtro"
            )

        with col2:
            data_ini = st.date_input(
                "Data Inicial:",
                value=date.today() - relativedelta(months=6),
                key="rel_super_data_ini"
            )
            data_fim = st.date_input(
                "Data Final:",
                value=date.today(),
                key="rel_super_data_fim"
            )

        col_btn1, col_btn2 = st.columns([1, 1])
        
        with col_btn1:
            gerar = st.button("🔍 Gerar Relatório", use_container_width=True, key="btn_rel_super")
        
        with col_btn2:
            gerar_detalhado = st.button("📊 Ver Detalhamento por Lotação", use_container_width=True, key="btn_rel_detalhado")

        if gerar or gerar_detalhado:
            with st.spinner("Gerando relatório..."):
                fig = self.relatorios.grafico_cobertura_superintendencia_top10()
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Não há dados suficientes para gerar o gráfico.")

                df_super = self.relatorios.cobertura_detalhada_por_superintendencia(
                    superintendencia_filtro,
                    data_ini,
                    data_fim
                )

                if not df_super.empty:
                    st.subheader("📊 Cobertura por Superintendência")
                    
                    total_servidores = df_super['total_servidores'].sum()
                    total_vacinados = df_super['total_vacinados'].sum()
                    cobertura_geral = (total_vacinados / total_servidores * 100) if total_servidores > 0 else 0

                    col_met1, col_met2, col_met3 = st.columns(3)
                    with col_met1:
                        st.metric("Total Servidores", f"{total_servidores:,}")
                    with col_met2:
                        st.metric("Servidores Vacinados", f"{total_vacinados:,}")
                    with col_met3:
                        st.metric("Cobertura Geral", f"{cobertura_geral:.1f}%")

                    st.dataframe(
                        df_super,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "superintendencia": "Superintendência",
                            "total_servidores": "Total Servidores",
                            "vacinados_periodo": "Vacinados (Período)",
                            "total_vacinados": "Total Vacinados",
                            "cobertura_periodo": "Cobertura Período (%)",
                            "cobertura_total": "Cobertura Total (%)"
                        }
                    )

                    if gerar_detalhado or superintendencia_filtro != "TODAS":
                        st.subheader("📋 Detalhamento por Lotação")
                        
                        df_detalhado = self.relatorios.cobertura_por_superintendencia_lotacao(
                            superintendencia_filtro
                        )
                        
                        if not df_detalhado.empty:
                            st.dataframe(
                                df_detalhado,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "superintendencia": "Superintendência",
                                    "lotacao": "Lotação",
                                    "total_servidores": "Total Servidores",
                                    "servidores_vacinados": "Vacinados",
                                    "cobertura_percentual": "Cobertura (%)"
                                }
                            )

                            if superintendencia_filtro != "TODAS" and len(df_detalhado) > 0:
                                fig2 = px.bar(
                                    df_detalhado.head(15),
                                    x='lotacao',
                                    y=['total_servidores', 'servidores_vacinados'],
                                    title=f'Cobertura por Lotação - {superintendencia_filtro}',
                                    barmode='group',
                                    labels={'value': 'Quantidade', 'variable': 'Tipo'}
                                )
                                st.plotly_chart(fig2, use_container_width=True)
                        else:
                            st.info("Nenhuma lotação encontrada para esta superintendência.")
                else:
                    st.info("Nenhum dado encontrado para os filtros selecionados.")

        with st.expander("📈 Estatísticas por Superintendência"):
            query = """
                SELECT 
                    s.superintendencia,
                    COUNT(DISTINCT s.id_comp) as total_servidores,
                    COUNT(DISTINCT d.id_comp) as total_vacinados,
                    COUNT(DISTINCT s.lotacao) as total_lotacoes,
                    ROUND((COUNT(DISTINCT d.id_comp) * 100.0 / COUNT(DISTINCT s.id_comp)), 1) as cobertura
                FROM servidores s
                LEFT JOIN doses d ON s.id_comp = d.id_comp
                WHERE s.situacao_funcional = 'ATIVO'
                  AND s.superintendencia IS NOT NULL
                  AND s.superintendencia != ''
                GROUP BY s.superintendencia
                HAVING total_servidores > 0
                ORDER BY total_servidores DESC
            """
            
            df_stats = self.db.read_sql(query)
            if not df_stats.empty:
                st.dataframe(df_stats, use_container_width=True, hide_index=True)
                
                csv = df_stats.to_csv(index=False)
                st.download_button(
                    "📥 Exportar CSV",
                    csv,
                    f"estatisticas_superintendencias_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True
                )
    
    def _render_servidores(self):
        """Renderiza relatório de servidores"""
        st.subheader("👥 Relatório de Servidores")

        busca_servidor = st.text_input(
            "Buscar servidor:",
            placeholder="Nome, CPF ou matrícula",
            key="rel_busca_servidor"
        )

        if busca_servidor:
            with st.spinner("Buscando..."):
                servidores = self.servidores.buscar_servidores(busca_servidor, limit=5)

                if not servidores.empty:
                    for _, servidor in servidores.iterrows():
                        with st.container():
                            relatorio = self.relatorios_gerenciais.gerar_relatorio_servidor(
                                str(servidor['id_comp'])
                            )

                            if relatorio:
                                st.markdown(f"### 📋 Ficha de {servidor['nome']}")

                                col_info1, col_info2 = st.columns(2)

                                with col_info1:
                                    st.markdown(f"""
                                    **CPF:** {Security.formatar_cpf(servidor['cpf'])}
                                    **Idade:** {relatorio.get('idade', 'N/I')} anos
                                    **Superintendência:** {servidor.get('superintendencia', 'N/I')}
                                    **Lotação:** {servidor['lotacao']}
                                    **Local Físico:** {servidor.get('lotacao_fisica', 'N/I')}
                                    **Cargo:** {servidor.get('cargo', 'N/I')}
                                    **Situação:** {servidor.get('situacao_funcional', 'ATIVO')}
                                    """)

                                with col_info2:
                                    st.markdown(f"""
                                    **Matrícula:** {servidor['numfunc']}-{servidor['numvinc']}
                                    **Admissão:** {Formatters.formatar_data_br(servidor.get('data_admissao'))}
                                    **Telefone:** {servidor.get('telefone', 'N/I')}
                                    **E-mail:** {servidor.get('email', 'N/I')}
                                    **Total de Doses:** {relatorio.get('total_doses', 0)}
                                    """)

                                if relatorio['historico_vacinacao']:
                                    st.subheader("💉 Histórico de Vacinação")

                                    df_historico = pd.DataFrame(relatorio['historico_vacinacao'])
                                    df_historico['data_ap'] = df_historico['data_ap'].apply(Formatters.formatar_data_br)
                                    df_historico['data_ret'] = df_historico['data_ret'].apply(Formatters.formatar_data_br)

                                    st.dataframe(
                                        df_historico[['vacina', 'dose', 'data_ap', 'data_ret', 'lote',
                                                     'local_aplicacao', 'nome_campanha']],
                                        use_container_width=True,
                                        hide_index=True,
                                        column_config={
                                            "vacina": "Vacina",
                                            "dose": "Dose",
                                            "data_ap": "Data Aplicação",
                                            "data_ret": "Data Retorno",
                                            "lote": "Lote",
                                            "local_aplicacao": "Local",
                                            "nome_campanha": "Campanha"
                                        }
                                    )

                                    vacinas_count = df_historico['vacina'].value_counts()
                                    if not vacinas_count.empty:
                                        fig = px.bar(
                                            x=vacinas_count.index,
                                            y=vacinas_count.values,
                                            title=f'Vacinas Aplicadas - {servidor["nome"]}',
                                            labels={'x': 'Vacina', 'y': 'Quantidade'}
                                        )
                                        st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.info("📭 Nenhum registro de vacinação encontrado.")

                                if st.button("📄 Gerar Ficha PDF", key=f"pdf_serv_{servidor['id_comp']}"):
                                    with st.spinner("Gerando PDF..."):
                                        try:
                                            pdf_bytes = RelatorioPDFService.gerar_ficha_cadastral_pdf(
                                                CONFIG.logo_path,
                                                relatorio['servidor'],
                                                relatorio['historico_vacinacao']
                                            )

                                            st.download_button(
                                                "📥 Baixar Ficha PDF",
                                                data=pdf_bytes,
                                                file_name=f"ficha_{servidor['nome'].replace(' ', '_')}_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
                                                mime="application/pdf",
                                                use_container_width=True
                                            )
                                        except Exception as e:
                                            st.error(f"Erro ao gerar PDF: {str(e)}")

                                st.markdown("---")
                else:
                    st.info("📭 Nenhum servidor encontrado.")