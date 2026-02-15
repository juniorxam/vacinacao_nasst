"""
produtividade.py - Página de relatório de produtividade por usuário
"""

from datetime import date, timedelta, datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from dateutil.relativedelta import relativedelta

from config import CONFIG
from core.security import Formatters
from ui.components import UIComponents


class ProdutividadePage:
    """Página de relatório de produtividade por usuário"""

    def __init__(self, db, auth):
        self.db = db
        self.auth = auth

    def render(self):
        """Renderiza página de produtividade"""
        st.title("📊 Relatório de Produtividade por Usuário")
        UIComponents.breadcrumb("🏠 Início", "Produtividade")

        if not self.auth.verificar_permissoes(st.session_state.nivel_acesso, "OPERADOR"):
            st.error("❌ Apenas operadores e administradores podem acessar este relatório.")
            return

        # Explicação sobre a contagem
        with st.expander("ℹ️ Como é calculada a produtividade"):
            st.markdown("""
            ### Como funciona a contagem:
            
            - **Cada registro de vacinação conta como 1 ponto**, independentemente de como foi inserido:
              - ✅ Registro manual (vacinação individual)
              - ✅ Importação em lote (planilha)
              - ✅ Importação do Meu SUS Digital (PDF)
            
            - **Filtro por data**: Considera a **data em que o registro foi cadastrado** no sistema (`data_registro`), não a data da aplicação.
            
            - **Usuário considerado**: O campo `usuario_registro` armazena o login de quem cadastrou a vacinação.
            """)

        # Filtros
        col1, col2, col3 = st.columns(3)

        with col1:
            periodo = st.selectbox(
                "Período:",
                ["Hoje", "Últimos 7 dias", "Últimos 30 dias", "Este mês", "Mês anterior", "Personalizado"],
                key="filtro_periodo_prod"
            )

        with col2:
            if periodo == "Personalizado":
                data_inicio = st.date_input(
                    "Data inicial:",
                    value=date.today() - timedelta(days=30),
                    key="data_inicio_prod"
                )
            else:
                data_inicio = self._calcular_data_inicio(periodo)
                st.text_input(
                    "Data inicial:",
                    value=data_inicio.strftime("%d/%m/%Y"),
                    disabled=True,
                    key="data_inicio_display_prod"
                )

        with col3:
            if periodo == "Personalizado":
                data_fim = st.date_input(
                    "Data final:",
                    value=date.today(),
                    key="data_fim_prod"
                )
            else:
                data_fim = date.today()
                st.text_input(
                    "Data final:",
                    value=data_fim.strftime("%d/%m/%Y"),
                    disabled=True,
                    key="data_fim_display_prod"
                )

        # CORREÇÃO: Botão para gerar relatório - remover width, usar use_container_width
        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
        with col_btn2:
            if st.button(
                "📊 Gerar Relatório de Produtividade",
                type="primary",
                use_container_width=True,  # CORRIGIDO: width -> use_container_width
                key="btn_gerar_prod"
            ):
                self._gerar_relatorio(data_inicio, data_fim)

    def _calcular_data_inicio(self, periodo):
        """Calcula a data de início baseada no período selecionado"""
        hoje = date.today()

        if periodo == "Hoje":
            return hoje
        elif periodo == "Últimos 7 dias":
            return hoje - timedelta(days=7)
        elif periodo == "Últimos 30 dias":
            return hoje - timedelta(days=30)
        elif periodo == "Este mês":
            return date(hoje.year, hoje.month, 1)
        elif periodo == "Mês anterior":
            ultimo_mes = hoje - relativedelta(months=1)
            return date(ultimo_mes.year, ultimo_mes.month, 1)
        else:
            return hoje - timedelta(days=30)

    def _gerar_relatorio(self, data_inicio, data_fim):
        """Gera o relatório de produtividade baseado na data de cadastro"""
        with st.spinner("Gerando relatório de produtividade..."):
            
            query_usuarios = """
                SELECT 
                    u.nome,
                    u.login,
                    u.nivel_acesso,
                    COUNT(d.id) as total_registros,
                    COUNT(DISTINCT d.id_comp) as servidores_atendidos,
                    MIN(d.data_registro) as primeiro_registro,
                    MAX(d.data_registro) as ultimo_registro
                FROM usuarios u
                LEFT JOIN doses d ON u.nome = d.usuario_registro
                    AND date(d.data_registro) BETWEEN ? AND ?
                WHERE u.ativo = 1
                GROUP BY u.login, u.nome, u.nivel_acesso
                ORDER BY total_registros DESC
            """

            df_usuarios = self.db.read_sql(
                query_usuarios,
                (data_inicio.isoformat(), data_fim.isoformat())
            )

            # Buscar totais gerais para debug
            total_periodo = self.db.fetchone(
                """
                SELECT COUNT(*) as total 
                FROM doses 
                WHERE date(data_registro) BETWEEN ? AND ?
                """,
                (data_inicio.isoformat(), data_fim.isoformat())
            )
            total_registros_periodo = total_periodo['total'] if total_periodo else 0

            # Diagnóstico para ajudar a identificar problemas
            with st.expander("🔍 Informações de Diagnóstico"):
                st.write(f"**Período analisado:** {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
                st.write(f"**Total de registros no período:** {total_registros_periodo}")
                
                # Amostra de registros no período
                amostra = self.db.read_sql("""
                    SELECT 
                        data_registro, 
                        usuario_registro, 
                        vacina, 
                        id_comp,
                        CASE 
                            WHEN local_aplicacao = 'Importado do Meu SUS' THEN 'Importado PDF'
                            WHEN local_aplicacao LIKE '%lote%' THEN 'Importado Lote'
                            ELSE 'Manual'
                        END as tipo_importacao
                    FROM doses 
                    WHERE date(data_registro) BETWEEN ? AND ?
                    ORDER BY data_registro DESC 
                    LIMIT 10
                """, (data_inicio.isoformat(), data_fim.isoformat()))
                
                if not amostra.empty:
                    st.write("**Últimos 10 registros no período:**")
                    st.dataframe(amostra, use_container_width=True)

            if df_usuarios.empty or df_usuarios['total_registros'].sum() == 0:
                st.warning(
                    f"⚠️ Nenhum registro encontrado no período de "
                    f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
                )
                st.info("💡 **Dicas:**")
                st.markdown("""
                - Verifique se há vacinações **cadastradas** no período selecionado (use a data de cadastro, não a data da aplicação)
                - Experimente um período maior (ex: Últimos 30 dias)
                - Confira se os usuários estão registrando as vacinações corretamente
                """)
                return

            # Métricas gerais
            st.subheader("📈 Métricas Gerais do Período")

            col_met1, col_met2, col_met3, col_met4 = st.columns(4)

            with col_met1:
                total_registros = int(df_usuarios['total_registros'].sum())
                st.metric("Total de Vacinações", f"{total_registros:,}")

            with col_met2:
                usuarios_ativos = len(df_usuarios[df_usuarios['total_registros'] > 0])
                st.metric("Usuários Ativos", usuarios_ativos)

            with col_met3:
                total_usuarios = len(df_usuarios)
                st.metric("Total de Usuários", total_usuarios)

            with col_met4:
                media_por_usuario = total_registros / usuarios_ativos if usuarios_ativos > 0 else 0
                st.metric("Média por Usuário", f"{media_por_usuario:.1f}")

            # Estatísticas adicionais
            col_est1, col_est2, col_est3 = st.columns(3)
            
            with col_est1:
                # Calcular média diária
                dias_periodo = (data_fim - data_inicio).days + 1
                media_diaria = total_registros / dias_periodo if dias_periodo > 0 else 0
                st.metric("Média Diária", f"{media_diaria:.1f}")
            
            with col_est2:
                # Melhor dia (requer consulta adicional)
                melhor_dia = self.db.fetchone("""
                    SELECT date(data_registro) as dia, COUNT(*) as total
                    FROM doses
                    WHERE date(data_registro) BETWEEN ? AND ?
                    GROUP BY dia
                    ORDER BY total DESC
                    LIMIT 1
                """, (data_inicio.isoformat(), data_fim.isoformat()))
                
                if melhor_dia:
                    dia_formatado = datetime.strptime(melhor_dia['dia'], '%Y-%m-%d').strftime('%d/%m/%Y')
                    st.metric("Melhor Dia", f"{dia_formatado} ({melhor_dia['total']})")
                else:
                    st.metric("Melhor Dia", "-")
            
            with col_est3:
                # Total de servidores atendidos
                total_servidores = int(df_usuarios['servidores_atendidos'].sum())
                st.metric("Servidores Atendidos", f"{total_servidores:,}")

            st.markdown("---")

            # Ranking de produtividade
            st.subheader("🏆 Ranking de Vacinações por Usuário")

            df_ranking = df_usuarios[df_usuarios['total_registros'] > 0].copy()

            if not df_ranking.empty:
                # Formata as datas
                df_ranking['primeiro_registro'] = pd.to_datetime(
                    df_ranking['primeiro_registro']
                ).dt.strftime('%d/%m/%Y %H:%M')
                df_ranking['ultimo_registro'] = pd.to_datetime(
                    df_ranking['ultimo_registro']
                ).dt.strftime('%d/%m/%Y %H:%M')

                # Adiciona coluna de participação percentual
                df_ranking['participacao'] = (
                    df_ranking['total_registros'] / total_registros * 100
                ).round(1)

                # Cria coluna de posição
                df_ranking['posicao'] = range(1, len(df_ranking) + 1)

                # Gráfico de barras - Top 10
                fig = px.bar(
                    df_ranking.head(10),
                    x='nome',
                    y='total_registros',
                    title='Top 10 Usuários por Registros de Vacinação',
                    labels={'total_registros': 'Número de Registros', 'nome': 'Usuário'},
                    color='total_registros',
                    color_continuous_scale='viridis',
                    text='total_registros'
                )
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

                # Gráfico de pizza - Distribuição
                fig_pizza = px.pie(
                    df_ranking.head(8),
                    values='total_registros',
                    names='nome',
                    title='Distribuição de Registros por Usuário (Top 8)'
                )
                st.plotly_chart(fig_pizza, use_container_width=True)

                # Tabela completa
                st.subheader("📋 Tabela Completa de Produtividade")
                st.dataframe(
                    df_ranking[[
                        'posicao', 'nome', 'login', 'nivel_acesso',
                        'total_registros', 'servidores_atendidos',
                        'participacao', 'primeiro_registro', 'ultimo_registro'
                    ]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "posicao": "🏆 Pos.",
                        "nome": "Nome",
                        "login": "Login",
                        "nivel_acesso": "Nível",
                        "total_registros": "Registros",
                        "servidores_atendidos": "Servidores",
                        "participacao": "Participação (%)",
                        "primeiro_registro": "Primeiro Registro",
                        "ultimo_registro": "Último Registro"
                    }
                )

                # Usuários sem registros
                df_inativos = df_usuarios[df_usuarios['total_registros'] == 0]
                if not df_inativos.empty:
                    with st.expander(f"👤 Usuários sem registros no período ({len(df_inativos)})"):
                        st.dataframe(
                            df_inativos[['nome', 'login', 'nivel_acesso']],
                            use_container_width=True,
                            hide_index=True
                        )

            st.markdown("---")

            # Detalhamento por usuário
            st.subheader("📋 Detalhamento por Usuário")

            # Seleciona usuário para detalhar
            usuarios_lista = df_ranking['nome'].tolist() if not df_ranking.empty else []
            if usuarios_lista:
                usuario_selecionado = st.selectbox(
                    "Selecione um usuário para ver detalhes:",
                    usuarios_lista,
                    key="select_usuario_detalhe_prod"
                )

                if usuario_selecionado:
                    login_selecionado = df_ranking[
                        df_ranking['nome'] == usuario_selecionado
                    ]['login'].iloc[0]

                    # Detalhamento das vacinações do usuário (usando data_registro)
                    query_detalhe = """
                        SELECT 
                            d.data_registro,
                            d.data_ap,
                            d.vacina,
                            d.dose,
                            s.nome as servidor_nome,
                            s.cpf,
                            s.lotacao,
                            s.superintendencia,
                            c.nome_campanha,
                            CASE 
                                WHEN d.local_aplicacao = 'Importado do Meu SUS' THEN 'Importado PDF'
                                WHEN d.local_aplicacao LIKE '%lote%' THEN 'Importado Lote'
                                ELSE 'Manual'
                            END as tipo_registro
                        FROM doses d
                        LEFT JOIN servidores s ON d.id_comp = s.id_comp
                        LEFT JOIN campanhas c ON d.campanha_id = c.id
                        WHERE d.usuario_registro = ? 
                            AND date(d.data_registro) BETWEEN ? AND ?
                        ORDER BY d.data_registro DESC
                    """

                    df_detalhe = self.db.read_sql(
                        query_detalhe,
                        (login_selecionado, data_inicio.isoformat(), data_fim.isoformat())
                    )

                    if not df_detalhe.empty:
                        df_detalhe['data_registro'] = pd.to_datetime(
                            df_detalhe['data_registro']
                        ).dt.strftime('%d/%m/%Y %H:%M')
                        df_detalhe['data_ap'] = pd.to_datetime(
                            df_detalhe['data_ap']
                        ).dt.strftime('%d/%m/%Y')

                        # Contagem por tipo de registro
                        st.subheader(f"📊 Análise de {usuario_selecionado}")
                        
                        col_tipo1, col_tipo2, col_tipo3 = st.columns(3)
                        
                        with col_tipo1:
                            total_manual = len(df_detalhe[df_detalhe['tipo_registro'] == 'Manual'])
                            st.metric("Registros Manuais", total_manual)
                        
                        with col_tipo2:
                            total_importado = len(df_detalhe[df_detalhe['tipo_registro'] == 'Importado Lote'])
                            st.metric("Importações em Lote", total_importado)
                        
                        with col_tipo3:
                            total_pdf = len(df_detalhe[df_detalhe['tipo_registro'] == 'Importado PDF'])
                            st.metric("Importações Meu SUS", total_pdf)

                        st.dataframe(
                            df_detalhe,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "data_registro": "Data Cadastro",
                                "data_ap": "Data Aplicação",
                                "vacina": "Vacina",
                                "dose": "Dose",
                                "servidor_nome": "Servidor",
                                "cpf": "CPF",
                                "lotacao": "Lotação",
                                "superintendencia": "Superintendência",
                                "nome_campanha": "Campanha",
                                "tipo_registro": "Tipo"
                            }
                        )

                        # Gráfico de atividades por dia para este usuário
                        df_detalhe['data'] = pd.to_datetime(
                            df_detalhe['data_registro'].str.split(' ').str[0], 
                            format='%d/%m/%Y'
                        ).dt.date
                        atividades_por_dia = df_detalhe.groupby('data').size().reset_index(
                            name='quantidade'
                        )

                        fig_dia = px.bar(
                            atividades_por_dia,
                            x='data',
                            y='quantidade',
                            title=f'Registros por Dia - {usuario_selecionado}',
                            labels={'quantidade': 'Registros', 'data': 'Data'},
                            text='quantidade'
                        )
                        fig_dia.update_traces(textposition='outside')
                        st.plotly_chart(fig_dia, use_container_width=True)

            st.markdown("---")

            # Exportar relatório
            st.subheader("📥 Exportar Relatório")

            col_exp1, col_exp2, col_exp3 = st.columns(3)

            with col_exp1:
                csv = df_ranking.to_csv(index=False)
                st.download_button(
                    "📥 CSV - Ranking",
                    csv,
                    f"produtividade_ranking_{date.today().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    use_container_width=True,
                    key="btn_csv_ranking"
                )

            with col_exp2:
                if 'df_detalhe' in locals() and not df_detalhe.empty:
                    csv_detalhe = df_detalhe.to_csv(index=False)
                    st.download_button(
                        "📥 CSV - Detalhes",
                        csv_detalhe,
                        f"produtividade_detalhes_{date.today().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        use_container_width=True,
                        key="btn_csv_detalhe"
                    )

            with col_exp3:
                # Relatório consolidado em Excel
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_ranking.to_excel(writer, sheet_name='Ranking', index=False)
                    if 'df_detalhe' in locals() and not df_detalhe.empty:
                        df_detalhe.to_excel(
                            writer,
                            sheet_name=f'Detalhes_{usuario_selecionado}',
                            index=False
                        )
                    
                    # Adicionar resumo do período
                    resumo = pd.DataFrame([{
                        'Período': f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}",
                        'Total Registros': total_registros,
                        'Usuários Ativos': usuarios_ativos,
                        'Média por Usuário': round(media_por_usuario, 1),
                        'Servidores Atendidos': total_servidores
                    }])
                    resumo.to_excel(writer, sheet_name='Resumo', index=False)

                st.download_button(
                    "📊 Excel Completo",
                    output.getvalue(),
                    f"produtividade_completa_{date.today().strftime('%Y%m%d')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="btn_excel_completo"
                )