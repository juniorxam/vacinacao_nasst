"""
campanhas.py - Página de gerenciamento de campanhas
"""

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from config import CONFIG
from core.security import Formatters
from core.auth_service import AuditLog  # CORRIGIDO: import específico
from ui.components import UIComponents


class CampanhasPage:
    """Página de campanhas"""
    
    def __init__(self, db, campanhas, vacinacao, auth, relatorios_gerenciais):
        self.db = db
        self.campanhas = campanhas
        self.vacinacao = vacinacao
        self.auth = auth
        self.relatorios_gerenciais = relatorios_gerenciais
        
        self._cache_vacinas = None
    
    def _get_cached_vacinas(self):
        if self._cache_vacinas is None:
            self._cache_vacinas = self.vacinacao.listar_vacinas_ativas()
        return self._cache_vacinas
    
    def render(self):
        """Renderiza página de campanhas"""
        st.title("📅 Campanhas de Vacinação")
        UIComponents.breadcrumb("🏠 Início", "Campanhas")

        tab1, tab2, tab3 = st.tabs([
            "📋 Listar Campanhas", "➕ Nova Campanha", "📊 Relatórios"
        ])

        with tab1:
            self._render_listar()

        with tab2:
            self._render_nova()

        with tab3:
            self._render_relatorios()
    
    def _render_listar(self):
        """Renderiza lista de campanhas"""
        st.subheader("📋 Campanhas Cadastradas")

        col1, col2 = st.columns(2)

        with col1:
            filtro_status = st.selectbox(
                "Status:",
                ["TODOS", "PLANEJADA", "ATIVA", "CONCLUÍDA", "CANCELADA"],
                key="filtro_status_campanhas"
            )

        with col2:
            filtro_ano = st.selectbox(
                "Ano:",
                ["TODOS"] + [str(ano) for ano in range(2020, 2031)],
                key="filtro_ano_campanhas"
            )

        # Botão de busca
        if st.button("🔍 Buscar Campanhas", type="primary", use_container_width=True):
            where_clauses = []
            params = []

            if filtro_status != "TODOS":
                where_clauses.append("status = ?")
                params.append(filtro_status)

            if filtro_ano != "TODOS":
                where_clauses.append("strftime('%Y', data_inicio) = ?")
                params.append(filtro_ano)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            query = f"""
                SELECT c.*,
                       COUNT(d.id) as doses_aplicadas,
                       COUNT(DISTINCT d.id_comp) as servidores_atendidos
                FROM campanhas c
                LEFT JOIN doses d ON c.id = d.campanha_id
                WHERE {where_sql}
                GROUP BY c.id
                ORDER BY c.data_inicio DESC
            """

            campanhas = self.db.read_sql(query, params)
            st.session_state.campanhas_filtradas = campanhas

        # Exibir resultados
        if st.session_state.get('campanhas_filtradas') is not None:
            campanhas = st.session_state.campanhas_filtradas

            if not campanhas.empty:
                st.success(f"✅ {len(campanhas)} campanhas encontradas")

                for _, campanha in campanhas.iterrows():
                    with st.container():
                        # Container com borda para cada campanha
                        st.markdown(f"""
                        <div style="border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 15px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h3 style="margin: 0;">{self._get_status_icon(campanha['status'])} {campanha['nome_campanha']}</h3>
                                    <p style="color: #666; margin: 5px 0;">Vacina: {campanha['vacina']}</p>
                                </div>
                                <div style="text-align: right;">
                                    <p style="margin: 0;"><strong>Período:</strong> {Formatters.formatar_data_br(campanha['data_inicio'])} a {Formatters.formatar_data_br(campanha['data_fim'])}</p>
                                    <p style="margin: 0;"><strong>Doses:</strong> {campanha['doses_aplicadas']} | <strong>Servidores:</strong> {campanha['servidores_atendidos']}</p>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        # Ações da campanha
                        col_acoes1, col_acoes2, col_acoes3, col_acoes4 = st.columns([1, 1, 1, 3])

                        with col_acoes1:
                            if st.button("📊 Relatório", key=f"rel_camp_{campanha['id']}", use_container_width=True):
                                st.session_state.rel_campanha_id = int(campanha['id'])
                                st.session_state.rel_campanha_nome = campanha['nome_campanha']
                                st.rerun()

                        with col_acoes2:
                            if st.button("✏️ Editar", key=f"edit_camp_{campanha['id']}", use_container_width=True, disabled=True):
                                st.info("Funcionalidade em desenvolvimento")

                        with col_acoes3:
                            if st.session_state.nivel_acesso == 'ADMIN':
                                if st.button("🗑️ Excluir", key=f"del_camp_{campanha['id']}", type="secondary", use_container_width=True):
                                    st.session_state.campanha_excluir = {
                                        'id': int(campanha['id']),
                                        'nome': campanha['nome_campanha'],
                                        'doses': int(campanha['doses_aplicadas']) if campanha['doses_aplicadas'] else 0
                                    }
                                    st.rerun()

                        with col_acoes4:
                            with st.expander("📋 Detalhes"):
                                st.markdown(f"""
                                **Descrição:** {campanha.get('descricao', 'Não informada')}
                                **Público-alvo:** {campanha.get('publico_alvo', 'Todos')}
                                **Criado por:** {campanha.get('usuario_criacao', 'Sistema')}
                                **Data criação:** {Formatters.formatar_data_br(campanha.get('data_criacao'))}
                                """)

                        st.markdown("---")
            else:
                st.info("📭 Nenhuma campanha encontrada com os filtros selecionados.")

        # Modal de relatório
        if 'rel_campanha_id' in st.session_state:
            self._render_relatorio_campanha()

        # Modal de exclusão
        if 'campanha_excluir' in st.session_state:
            self._render_modal_exclusao()
    
    def _get_status_icon(self, status):
        """Retorna ícone para o status da campanha"""
        icons = {
            "PLANEJADA": "🟡",
            "ATIVA": "🟢",
            "CONCLUÍDA": "🔵",
            "CANCELADA": "🔴"
        }
        return icons.get(status, "⚪")
    
    def _render_relatorio_campanha(self):
        """Renderiza relatório detalhado da campanha"""
        campanha_id = st.session_state.rel_campanha_id
        campanha_nome = st.session_state.rel_campanha_nome

        st.markdown("---")
        st.subheader(f"📊 Relatório da Campanha: {campanha_nome}")

        # Buscar dados da campanha
        campanha = self.db.fetchone(
            "SELECT * FROM campanhas WHERE id = ?",
            (campanha_id,)
        )

        if not campanha:
            st.error("Campanha não encontrada!")
            if st.button("🔙 Voltar", use_container_width=True):
                del st.session_state.rel_campanha_id
                del st.session_state.rel_campanha_nome
                st.rerun()
            return

        # Estatísticas da campanha
        stats = self.db.fetchone(
            """
            SELECT 
                COUNT(*) as total_doses,
                COUNT(DISTINCT id_comp) as total_servidores,
                MIN(data_ap) as primeira_dose,
                MAX(data_ap) as ultima_dose
            FROM doses 
            WHERE campanha_id = ?
            """,
            (campanha_id,)
        )

        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de Doses", stats['total_doses'] if stats and stats['total_doses'] else 0)

        with col2:
            st.metric("Servidores Atendidos", stats['total_servidores'] if stats and stats['total_servidores'] else 0)

        with col3:
            st.metric("Data Início", Formatters.formatar_data_br(campanha['data_inicio']))

        with col4:
            st.metric("Data Fim", Formatters.formatar_data_br(campanha['data_fim']))

        # Informações da campanha
        col_info1, col_info2 = st.columns(2)

        with col_info1:
            st.markdown(f"""
            **Status:** {campanha['status']}
            **Vacina:** {campanha['vacina']}
            **Público-alvo:** {campanha['publico_alvo']}
            """)

        with col_info2:
            st.markdown(f"""
            **Criado por:** {campanha.get('usuario_criacao', 'Sistema')}
            **Data criação:** {Formatters.formatar_data_br(campanha.get('data_criacao'))}
            """)

        if campanha.get('descricao'):
            st.markdown(f"**Descrição:** {campanha['descricao']}")

        # Lista de vacinações da campanha
        st.subheader("📋 Vacinações Realizadas")

        doses_df = self.db.read_sql(
            """
            SELECT 
                d.data_ap,
                d.vacina,
                d.dose,
                s.nome as servidor,
                s.cpf,
                s.lotacao,
                s.superintendencia,
                d.usuario_registro
            FROM doses d
            JOIN servidores s ON d.id_comp = s.id_comp
            WHERE d.campanha_id = ?
            ORDER BY d.data_ap DESC
            """,
            (campanha_id,)
        )

        if not doses_df.empty:
            # Formatar dados para exibição
            doses_df['data_ap'] = pd.to_datetime(doses_df['data_ap']).dt.strftime('%d/%m/%Y')
            doses_df['cpf'] = doses_df['cpf'].apply(lambda x: f"{x[:3]}.{x[3:6]}.{x[6:9]}-{x[9:]}" if len(str(x)) == 11 else x)

            st.dataframe(
                doses_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "data_ap": "Data",
                    "vacina": "Vacina",
                    "dose": "Dose",
                    "servidor": "Servidor",
                    "cpf": "CPF",
                    "lotacao": "Lotação",
                    "superintendencia": "Superintendência",
                    "usuario_registro": "Registrado por"
                }
            )

            # Gráfico de doses por dia
            doses_df['data'] = pd.to_datetime(doses_df['data_ap'], format='%d/%m/%Y')
            doses_por_dia = doses_df.groupby('data').size().reset_index(name='quantidade')

            if not doses_por_dia.empty:
                fig = px.line(
                    doses_por_dia,
                    x='data',
                    y='quantidade',
                    title='Doses Aplicadas por Dia',
                    labels={'data': 'Data', 'quantidade': 'Número de Doses'},
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)

            # Botões de exportação
            col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 2])

            with col_exp1:
                csv = doses_df.to_csv(index=False)
                st.download_button(
                    "📥 CSV",
                    csv,
                    f"campanha_{campanha_id}_doses.csv",
                    "text/csv",
                    use_container_width=True
                )

            with col_exp2:
                # Exportar relatório completo em Excel
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Informações da campanha
                    info_df = pd.DataFrame([{
                        'Campanha': campanha['nome_campanha'],
                        'Vacina': campanha['vacina'],
                        'Status': campanha['status'],
                        'Período': f"{Formatters.formatar_data_br(campanha['data_inicio'])} a {Formatters.formatar_data_br(campanha['data_fim'])}",
                        'Total Doses': stats['total_doses'] if stats else 0,
                        'Servidores': stats['total_servidores'] if stats else 0
                    }])
                    info_df.to_excel(writer, sheet_name='Informações', index=False)

                    # Doses aplicadas
                    doses_df.to_excel(writer, sheet_name='Doses Aplicadas', index=False)

                st.download_button(
                    "📊 Excel",
                    output.getvalue(),
                    f"campanha_{campanha_id}_relatorio.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.info("Nenhuma vacinação registrada nesta campanha.")

        if st.button("🔙 Voltar para Lista", use_container_width=True):
            del st.session_state.rel_campanha_id
            del st.session_state.rel_campanha_nome
            st.rerun()

    def _render_modal_exclusao(self):
        """Renderiza modal de confirmação de exclusão de campanha"""
        campanha = st.session_state.campanha_excluir

        st.markdown("---")
        st.error("⚠️ **CONFIRMAÇÃO DE EXCLUSÃO DE CAMPANHA**")

        # Usar markdown com HTML correto
        st.markdown(f"""
        <div style="background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px; padding: 15px; margin: 10px 0;">
            <h4 style="color: #856404; margin-top: 0;">Você está prestes a excluir permanentemente esta campanha:</h4>
            <ul style="margin-bottom: 10px;">
                <li><strong>ID:</strong> {campanha['id']}</li>
                <li><strong>Nome:</strong> {campanha['nome']}</li>
                <li><strong>Doses aplicadas:</strong> {campanha['doses']}</li>
            </ul>
        """, unsafe_allow_html=True)

        if campanha['doses'] > 0:
            st.warning(f"⚠️ **ATENÇÃO:** Esta campanha possui {campanha['doses']} doses aplicadas!")
            
            st.markdown("""
            <div style="margin-top: 5px; margin-bottom: 5px;">
                <p style="color: #dc3545; font-weight: bold; margin-bottom: 5px;">
                    A exclusão removerá a associação dessas doses à campanha, mas os registros de vacinação serão mantidos.
                </p>
                <p style="color: #666; font-style: italic;">
                    As vacinações continuarão existindo no sistema, mas perderão o vínculo com esta campanha.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="margin-top: 5px; margin-bottom: 5px;">
                <p style="color: #dc3545; font-weight: bold;">
                    Esta ação é IRREVERSÍVEL e a campanha será removida permanentemente do sistema.
                </p>
            </div>
            """, unsafe_allow_html=True)

        # Fechar a div principal
        st.markdown('</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("✅ Confirmar Exclusão", type="primary", use_container_width=True):
                with st.spinner("Excluindo campanha..."):
                    try:
                        with self.db.connect() as conn:
                            if campanha['doses'] > 0:
                                # Se tem doses, apenas desassociar (remover campanha_id)
                                conn.execute(
                                    "UPDATE doses SET campanha_id = NULL WHERE campanha_id = ?",
                                    (campanha['id'],)
                                )

                            # Excluir a campanha
                            conn.execute(
                                "DELETE FROM campanhas WHERE id = ?",
                                (campanha['id'],)
                            )

                        # CORRIGIDO: usar AuditLog diretamente
                        audit = AuditLog(self.db)
                        audit.registrar(
                            st.session_state.usuario_nome,
                            "CAMPANHAS",
                            "Excluiu campanha",
                            f"ID: {campanha['id']} | Nome: {campanha['nome']} | Doses afetadas: {campanha['doses']}"
                        )

                        st.success(f"✅ Campanha '{campanha['nome']}' excluída com sucesso!")
                        del st.session_state.campanha_excluir
                        if 'campanhas_filtradas' in st.session_state:
                            del st.session_state.campanhas_filtradas
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Erro ao excluir campanha: {str(e)}")

        with col2:
            if st.button("❌ Cancelar", use_container_width=True):
                del st.session_state.campanha_excluir
                st.rerun()

    
    def _render_nova(self):
        """Renderiza formulário de nova campanha"""
        st.subheader("➕ Nova Campanha de Vacinação")

        with st.form("form_nova_campanha", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                nome_campanha = st.text_input(
                    "Nome da Campanha:*",
                    placeholder="Ex: Campanha de Influenza 2024",
                    key="camp_nome"
                )

                vacina = st.selectbox(
                    "Vacina:*",
                    [""] + self._get_cached_vacinas(),
                    key="camp_vacina"
                )

                if vacina == "":
                    vacina = st.text_input(
                        "Outra vacina:",
                        placeholder="Digite o nome da vacina",
                        key="camp_outra_vacina"
                    )

            with col2:
                data_inicio = st.date_input(
                    "Data de Início:*",
                    value=date.today(),
                    key="camp_inicio"
                )

                data_fim = st.date_input(
                    "Data de Término:*",
                    value=date.today() + timedelta(days=30),
                    key="camp_fim"
                )

                status = st.selectbox(
                    "Status:*",
                    ["PLANEJADA", "ATIVA", "CONCLUÍDA", "CANCELADA"],
                    key="camp_status"
                )

            st.markdown("### 🎯 Público-Alvo")
            publico_opcoes = ["Todos os servidores", "Por superintendência", "Por lotação", "Por faixa etária"]
            publico_selecionados = st.multiselect(
                "Selecione o público-alvo:",
                publico_opcoes,
                default=["Todos os servidores"],
                key="camp_publico"
            )

            descricao = st.text_area(
                "Descrição/Objetivos:",
                placeholder="Descreva os objetivos, critérios e informações importantes da campanha...",
                height=150,
                key="camp_descricao"
            )

            st.markdown("*Campos obrigatórios")

            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

            with col_btn1:
                submit = st.form_submit_button(
                    "💾 Criar Campanha",
                    use_container_width=True,
                    type="primary"
                )

            with col_btn2:
                limpar = st.form_submit_button(
                    "🔄 Limpar",
                    use_container_width=True
                )

            with col_btn3:
                cancelar = st.form_submit_button(
                    "❌ Cancelar",
                    use_container_width=True,
                    type="secondary"
                )

            if submit:
                self._processar_criacao(nome_campanha, vacina, publico_selecionados, 
                                       data_inicio, data_fim, status, descricao)

            if cancelar:
                st.session_state.pagina_atual = "campanhas"
                st.rerun()
    
    def _processar_criacao(self, nome, vacina, publico, data_inicio, data_fim, status, descricao):
        """Processa criação de campanha"""
        if not nome.strip():
            st.error("❌ Nome da campanha é obrigatório!")
            st.stop()

        if not vacina.strip():
            st.error("❌ Vacina é obrigatória!")
            st.stop()

        if data_fim < data_inicio:
            st.error("❌ Data de término deve ser posterior à data de início!")
            st.stop()

        try:
            self.campanhas.criar_campanha(
                nome=nome.strip(),
                vacina=vacina.strip(),
                publico_alvo=publico,
                data_inicio=data_inicio,
                data_fim=data_fim,
                status=status,
                descricao=descricao.strip(),
                usuario=st.session_state.usuario_nome,
            )

            st.success("✅ Campanha criada com sucesso!")
            st.balloons()

            # Limpar cache de campanhas filtradas
            if 'campanhas_filtradas' in st.session_state:
                del st.session_state.campanhas_filtradas

        except Exception as e:
            st.error(f"❌ Erro ao criar campanha: {str(e)}")
    
    def _render_relatorios(self):
        """Renderiza relatórios de campanhas"""
        st.subheader("📊 Relatórios de Campanhas")

        if st.button("📈 Gerar Relatório Completo", use_container_width=True, type="primary"):
            with st.spinner("Gerando relatório..."):
                relatorio = self.relatorios_gerenciais.gerar_relatorio_campanhas()

                if relatorio:
                    st.success(f"✅ Relatório gerado: {relatorio['total_campanhas']} campanhas analisadas")

                    # Métricas principais
                    col_tot1, col_tot2, col_tot3 = st.columns(3)

                    with col_tot1:
                        st.metric("Total Campanhas", relatorio['total_campanhas'])

                    with col_tot2:
                        total_doses = sum(item.get('doses_aplicadas', 0) for item in relatorio['campanhas'])
                        st.metric("Total Doses", total_doses)

                    with col_tot3:
                        total_servidores = sum(item.get('servidores_atendidos', 0) for item in relatorio['campanhas'])
                        st.metric("Servidores Atendidos", total_servidores)

                    # Estatísticas por status
                    st.subheader("📊 Estatísticas por Status")
                    if relatorio['estatisticas_status']:
                        df_status = pd.DataFrame(relatorio['estatisticas_status'])

                        col_graf1, col_graf2 = st.columns(2)

                        with col_graf1:
                            st.dataframe(
                                df_status,
                                use_container_width=True,
                                hide_index=True,
                                column_config={
                                    "status": "Status",
                                    "total_campanhas": "Campanhas",
                                    "total_doses": "Doses"
                                }
                            )

                        with col_graf2:
                            fig = px.pie(
                                df_status,
                                values='total_campanhas',
                                names='status',
                                title='Distribuição de Campanhas por Status',
                                color_discrete_map={
                                    'PLANEJADA': '#FFA07A',
                                    'ATIVA': '#90EE90',
                                    'CONCLUÍDA': '#87CEEB',
                                    'CANCELADA': '#FF6B6B'
                                }
                            )
                            st.plotly_chart(fig, use_container_width=True)

                    # Lista de campanhas
                    st.subheader("📋 Lista de Campanhas")
                    df_campanhas = pd.DataFrame(relatorio['campanhas'])

                    if not df_campanhas.empty:
                        # Formatar datas
                        if 'data_inicio' in df_campanhas.columns:
                            df_campanhas['data_inicio'] = df_campanhas['data_inicio'].apply(Formatters.formatar_data_br)
                        if 'data_fim' in df_campanhas.columns:
                            df_campanhas['data_fim'] = df_campanhas['data_fim'].apply(Formatters.formatar_data_br)
                        if 'data_criacao' in df_campanhas.columns:
                            df_campanhas['data_criacao'] = pd.to_datetime(df_campanhas['data_criacao']).dt.strftime('%d/%m/%Y')

                        # Selecionar colunas para exibição
                        colunas_exibir = []
                        for col in ['nome_campanha', 'vacina', 'status', 'data_inicio', 'data_fim', 
                                   'doses_aplicadas', 'servidores_atendidos', 'usuario_criacao']:
                            if col in df_campanhas.columns:
                                colunas_exibir.append(col)

                        st.dataframe(
                            df_campanhas[colunas_exibir],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "nome_campanha": "Nome da Campanha",
                                "vacina": "Vacina",
                                "status": "Status",
                                "data_inicio": "Início",
                                "data_fim": "Término",
                                "doses_aplicadas": "Doses",
                                "servidores_atendidos": "Servidores",
                                "usuario_criacao": "Criado por"
                            }
                        )

                        # Botões de exportação
                        col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 2])

                        with col_exp1:
                            csv = df_campanhas.to_csv(index=False)
                            st.download_button(
                                "📥 CSV",
                                csv,
                                f"relatorio_campanhas_{date.today().strftime('%Y%m%d')}.csv",
                                "text/csv",
                                use_container_width=True
                            )

                        with col_exp2:
                            import io
                            output = io.BytesIO()
                            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                df_campanhas.to_excel(writer, sheet_name='Campanhas', index=False)
                                if relatorio['estatisticas_status']:
                                    df_status.to_excel(writer, sheet_name='Estatísticas', index=False)

                            st.download_button(
                                "📊 Excel",
                                output.getvalue(),
                                f"relatorio_campanhas_{date.today().strftime('%Y%m%d')}.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                    else:
                        st.info("Nenhuma campanha encontrada.")
                else:
                    st.info("📭 Nenhum dado disponível para gerar relatório.")