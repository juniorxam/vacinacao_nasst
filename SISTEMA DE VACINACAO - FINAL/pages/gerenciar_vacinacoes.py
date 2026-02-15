"""
gerenciar_vacinacoes.py - Página para gerenciar e excluir vacinações
"""

from datetime import date, timedelta, datetime
import pandas as pd
import streamlit as st

from config import CONFIG
from core.security import Security, Formatters
from ui.components import UIComponents
from core.auth_service import AuditLog


class GerenciarVacinacoesPage:
    """Página para gerenciar registros de vacinação"""
    
    def __init__(self, db, vacinacao, auth, audit):
        self.db = db
        self.vacinacao = vacinacao
        self.auth = auth
        self.audit = audit
    
    def render(self):
        """Renderiza página de gerenciamento de vacinações"""
        st.title("📋 Gerenciar Registros de Vacinação")
        UIComponents.breadcrumb("🏠 Início", "Gerenciar Vacinações")

        # Verificar permissão
        nivel_acesso = st.session_state.get('nivel_acesso', 'VISUALIZADOR')
        if nivel_acesso not in ['ADMIN', 'OPERADOR']:
            st.error("❌ Apenas administradores e operadores podem gerenciar registros de vacinação.")
            return

        # Abas
        tab1, tab2 = st.tabs(["🔍 Consultar e Excluir", "📊 Estatísticas"])

        with tab1:
            self._render_consulta_exclusao()
        
        with tab2:
            self._render_estatisticas()
    
    def _render_consulta_exclusao(self):
        """Renderiza consulta e exclusão de registros com seleção múltipla"""
        st.subheader("🔍 Consultar Registros de Vacinação")
        
        # Inicializar estado da sessão para seleção múltipla
        if 'registros_selecionados' not in st.session_state:
            st.session_state.registros_selecionados = []
        
        # Abas para diferentes modos de busca
        tab_busca1, tab_busca2, tab_busca3 = st.tabs(["📅 Por Período", "👤 Por Servidor", "🔎 Busca Livre"])
        
        with tab_busca1:
            self._render_busca_por_periodo()
        
        with tab_busca2:
            self._render_busca_por_servidor()
        
        with tab_busca3:
            self._render_busca_livre()
        
        # Exibir resultados se houver
        if 'registros_vacinacao' in st.session_state and st.session_state.registros_vacinacao is not None:
            df = st.session_state.registros_vacinacao
            if not df.empty:
                self._render_tabela_registros_com_selecao(df)
            else:
                st.info("Nenhum registro encontrado com os critérios selecionados.")
    
    def _render_busca_por_periodo(self):
        """Renderiza busca por período"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            periodo = st.selectbox(
                "Período:",
                ["Últimos 7 dias", "Últimos 30 dias", "Últimos 90 dias", "Este mês", "Mês anterior", "Personalizado"],
                key="periodo_consulta"
            )
        
        with col2:
            if periodo == "Personalizado":
                data_inicio = st.date_input(
                    "Data inicial:",
                    value=date.today() - timedelta(days=30),
                    key="data_inicio_consulta"
                )
                data_fim = st.date_input(
                    "Data final:",
                    value=date.today(),
                    key="data_fim_consulta"
                )
            else:
                data_inicio, data_fim = self._calcular_periodo(periodo)
                st.text_input("Período:", value=f"{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}", disabled=True)
        
        with col3:
            if st.session_state.nivel_acesso == 'ADMIN':
                # Listar usuários para filtrar
                usuarios_df = self.db.read_sql(
                    "SELECT login, nome FROM usuarios WHERE ativo = 1 ORDER BY nome"
                )
                usuarios_list = ["Todos"] + [f"{row['nome']} ({row['login']})" for _, row in usuarios_df.iterrows()]
                usuario_filtro = st.selectbox(
                    "Usuário:",
                    usuarios_list,
                    key="usuario_filtro_periodo"
                )
                
                # Extrair login do filtro
                if usuario_filtro != "Todos":
                    login = usuario_filtro.split('(')[-1].replace(')', '')
                else:
                    login = None
            else:
                # Operador vê apenas os próprios registros
                login = st.session_state.usuario_login
                st.info(f"Mostrando apenas seus registros: {st.session_state.usuario_nome}")
        
        # Botão de busca
        if st.button("🔍 Buscar por Período", type="primary", use_container_width=True, key="btn_busca_periodo"):
            with st.spinner("Buscando registros..."):
                df = self.vacinacao.listar_registros_por_periodo(
                    data_inicio, 
                    data_fim,
                    usuario=login if login != "Todos" else None
                )
                
                if not df.empty:
                    st.session_state.registros_vacinacao = df
                    st.session_state.registros_selecionados = []  # Limpar seleções anteriores
                    st.success(f"✅ Encontrados {len(df)} registros")
                else:
                    st.warning("Nenhum registro encontrado no período.")
                    st.session_state.registros_vacinacao = None
    
    def _render_busca_por_servidor(self):
        """Renderiza busca por servidor"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            busca_servidor = st.text_input(
                "Nome do servidor:",
                placeholder="Digite o nome do servidor...",
                key="busca_servidor_nome"
            )
        
        with col2:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            buscar = st.button("🔍 Buscar", key="btn_busca_servidor", use_container_width=True)
        
        if buscar and busca_servidor:
            with st.spinner("Buscando servidores..."):
                # Buscar servidores pelo nome
                from core.servidor_service import ServidoresService
                servidores_service = ServidoresService(self.db, None)
                servidores = servidores_service.buscar_servidores(busca_servidor, limit=20)
                
                if not servidores.empty:
                    st.session_state.servidores_encontrados = servidores
                else:
                    st.warning("Nenhum servidor encontrado com esse nome.")
                    st.session_state.servidores_encontrados = None
        
        # Exibir servidores encontrados
        if 'servidores_encontrados' in st.session_state and st.session_state.servidores_encontrados is not None:
            servidores_df = st.session_state.servidores_encontrados
            
            st.markdown("### 👥 Servidores Encontrados")
            
            # Selecionar servidor
            opcoes_servidor = {}
            for _, row in servidores_df.iterrows():
                cpf_formatado = Security.formatar_cpf(row['cpf'])
                opcoes_servidor[f"{row['nome']} ({cpf_formatado}) - {row['lotacao']}"] = row['id_comp']
            
            servidor_selecionado = st.selectbox(
                "Selecione o servidor para ver o histórico:",
                list(opcoes_servidor.keys()),
                key="select_servidor_historico"
            )
            
            if servidor_selecionado:
                id_comp = opcoes_servidor[servidor_selecionado]
                
                # Botão para ver histórico
                if st.button("📋 Ver Histórico de Vacinação", use_container_width=True, key="btn_ver_historico"):
                    with st.spinner("Carregando histórico..."):
                        historico = self.vacinacao.historico_servidor(id_comp)
                        
                        if not historico.empty:
                            # Adicionar coluna de servidor_nome para compatibilidade
                            historico['servidor_nome'] = servidor_selecionado.split(' (')[0]
                            st.session_state.registros_vacinacao = historico
                            st.session_state.registros_selecionados = []
                            st.success(f"✅ Encontrados {len(historico)} registros para este servidor")
                        else:
                            st.info("Este servidor não possui registros de vacinação.")
                            st.session_state.registros_vacinacao = None
    
    def _render_busca_livre(self):
        """Renderiza busca livre por texto"""
        col1, col2 = st.columns([3, 1])
        
        with col1:
            termo_busca = st.text_input(
                "Termo de busca:",
                placeholder="Vacina, lote, local, etc...",
                key="termo_busca_livre"
            )
        
        with col2:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            buscar = st.button("🔍 Buscar", key="btn_busca_livre", use_container_width=True)
        
        if buscar and termo_busca:
            with st.spinner("Buscando registros..."):
                query = """
                    SELECT 
                        d.id,
                        d.data_ap,
                        d.vacina,
                        d.dose,
                        d.lote,
                        d.local_aplicacao,
                        s.nome as servidor_nome,
                        s.cpf,
                        s.lotacao,
                        s.superintendencia,
                        d.usuario_registro,
                        d.data_registro
                    FROM doses d
                    JOIN servidores s ON d.id_comp = s.id_comp
                    WHERE d.vacina LIKE ? 
                       OR d.lote LIKE ? 
                       OR d.local_aplicacao LIKE ?
                       OR s.nome LIKE ?
                    ORDER BY d.data_ap DESC
                    LIMIT 200
                """
                like_term = f"%{termo_busca}%"
                df = self.db.read_sql(query, (like_term, like_term, like_term, like_term))
                
                if not df.empty:
                    st.session_state.registros_vacinacao = df
                    st.session_state.registros_selecionados = []
                    st.success(f"✅ Encontrados {len(df)} registros")
                else:
                    st.warning("Nenhum registro encontrado com esse termo.")
                    st.session_state.registros_vacinacao = None
    
    def _calcular_periodo(self, periodo):
        """Calcula datas baseado no período selecionado"""
        hoje = date.today()
        
        if periodo == "Últimos 7 dias":
            return hoje - timedelta(days=7), hoje
        elif periodo == "Últimos 30 dias":
            return hoje - timedelta(days=30), hoje
        elif periodo == "Últimos 90 dias":
            return hoje - timedelta(days=90), hoje
        elif periodo == "Este mês":
            return date(hoje.year, hoje.month, 1), hoje
        elif periodo == "Mês anterior":
            if hoje.month == 1:
                return date(hoje.year - 1, 12, 1), date(hoje.year, hoje.month, 1) - timedelta(days=1)
            else:
                return date(hoje.year, hoje.month - 1, 1), date(hoje.year, hoje.month, 1) - timedelta(days=1)
        else:
            return hoje - timedelta(days=30), hoje
    
    def _render_tabela_registros_com_selecao(self, df):
        """Renderiza tabela de registros com checkboxes para seleção múltipla"""
        st.subheader("📋 Registros Encontrados")
        
        # Verificar quais colunas existem no DataFrame
        colunas_disponiveis = df.columns.tolist()
        
        # Preparar dados para exibição
        df_display = df.copy()
        df_display['data_ap'] = pd.to_datetime(df_display['data_ap']).dt.strftime('%d/%m/%Y')
        if 'cpf' in df_display.columns:
            df_display['cpf'] = df_display['cpf'].apply(Security.formatar_cpf)
        if 'data_registro' in df_display.columns:
            df_display['data_registro'] = pd.to_datetime(df_display['data_registro']).dt.strftime('%d/%m/%Y %H:%M')
        
        # Estatísticas rápidas
        col_est1, col_est2, col_est3, col_est4 = st.columns(4)
        with col_est1:
            st.metric("Total de Registros", len(df_display))
        with col_est2:
            st.metric("Vacinas Diferentes", df_display['vacina'].nunique())
        with col_est3:
            st.metric("Servidores", df_display['servidor_nome'].nunique())
        with col_est4:
            st.metric("Selecionados", len(st.session_state.registros_selecionados))
        
        # Botões de ação em massa
        col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns([1, 1, 1, 1, 2])
        
        with col_btn1:
            if st.button("✅ Selecionar Todos", use_container_width=True):
                st.session_state.registros_selecionados = df['id'].tolist()
                st.rerun()
        
        with col_btn2:
            if st.button("❌ Limpar Seleção", use_container_width=True):
                st.session_state.registros_selecionados = []
                st.rerun()
        
        with col_btn3:
            if st.button("🔁 Inverter Seleção", use_container_width=True):
                todos_ids = set(df['id'].tolist())
                selecionados = set(st.session_state.registros_selecionados)
                st.session_state.registros_selecionados = list(todos_ids - selecionados)
                st.rerun()
        
        with col_btn4:
            # Botão de excluir selecionados (só aparece se houver seleção)
            if st.session_state.registros_selecionados:
                if st.button("🗑️ Excluir Selecionados", type="primary", use_container_width=True):
                    st.session_state.excluir_confirmacao = {
                        'quantidade': len(st.session_state.registros_selecionados),
                        'ids': st.session_state.registros_selecionados.copy()
                    }
                    st.rerun()
        
        # Paginação
        items_per_page = 10
        total_items = len(df_display)
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        
        if 'page_gerenciar' not in st.session_state:
            st.session_state.page_gerenciar = 1
        
        if st.session_state.page_gerenciar > total_pages:
            st.session_state.page_gerenciar = total_pages
        
        col_page1, col_page2, col_page3, col_page4, col_page5 = st.columns([2, 1, 2, 1, 2])
        
        with col_page1:
            st.write(f"Página {st.session_state.page_gerenciar} de {total_pages}")
        
        with col_page2:
            if st.button("◀️", disabled=st.session_state.page_gerenciar <= 1, key="prev_page"):
                st.session_state.page_gerenciar -= 1
                st.rerun()
        
        with col_page3:
            st.write(f"Mostrando {min(items_per_page, total_items)} registros por página")
        
        with col_page4:
            if st.button("▶️", disabled=st.session_state.page_gerenciar >= total_pages, key="next_page"):
                st.session_state.page_gerenciar += 1
                st.rerun()
        
        with col_page5:
            go_to_page = st.number_input(
                "Ir para página",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.page_gerenciar,
                step=1,
                key="go_to_page",
                label_visibility="collapsed"
            )
            if go_to_page != st.session_state.page_gerenciar:
                st.session_state.page_gerenciar = go_to_page
                st.rerun()
        
        # Índices da página atual
        start_idx = (st.session_state.page_gerenciar - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        
        # Criar DataFrame para exibição com checkbox
        df_pagina = df_display.iloc[start_idx:end_idx].copy()
        
        # Adicionar coluna de seleção
        df_pagina['Selecionar'] = df_pagina['id'].apply(
            lambda x: x in st.session_state.registros_selecionados
        )
        
        # Definir colunas para exibição baseado no que está disponível
        colunas_exibicao = ['Selecionar', 'id', 'data_ap', 'vacina', 'dose', 'servidor_nome']
        
        # Adicionar lote se disponível
        if 'lote' in df_pagina.columns:
            colunas_exibicao.append('lote')
        
        # Adicionar usuario_registro se disponível
        if 'usuario_registro' in df_pagina.columns:
            colunas_exibicao.append('usuario_registro')
        
        # Editor de dados com coluna de seleção
        edited_df = st.data_editor(
            df_pagina[colunas_exibicao],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Selecionar": st.column_config.CheckboxColumn(
                    "Selecionar",
                    help="Marque para selecionar este registro",
                    default=False,
                ),
                "id": "ID",
                "data_ap": "Data",
                "vacina": "Vacina",
                "dose": "Dose",
                "servidor_nome": "Servidor",
                "lote": "Lote",
                "usuario_registro": "Registrado por"
            },
            disabled=["id", "data_ap", "vacina", "dose", "servidor_nome", "lote", "usuario_registro"],
            key="data_editor_vacinas"
        )
        
        # Atualizar seleção baseado no editor
        if edited_df is not None:
            novos_selecionados = set(st.session_state.registros_selecionados)
            for _, row in edited_df.iterrows():
                if row['Selecionar']:
                    novos_selecionados.add(row['id'])
                else:
                    novos_selecionados.discard(row['id'])
            st.session_state.registros_selecionados = list(novos_selecionados)
        
        # Modal de confirmação de exclusão
        if 'excluir_confirmacao' in st.session_state:
            self._render_modal_exclusao_multipla()
    
    def _render_modal_exclusao_multipla(self):
        """Renderiza modal de confirmação de exclusão múltipla"""
        dados = st.session_state.excluir_confirmacao
        quantidade = dados['quantidade']
        ids = dados['ids']
        
        st.markdown("---")
        st.error("⚠️ **CONFIRMAÇÃO DE EXCLUSÃO EM MASSA**")
        
        st.markdown(f"""
        <div style="background-color: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px; padding: 15px; margin: 10px 0;">
            <h4 style="color: #856404;">Você está prestes a excluir permanentemente <strong>{quantidade}</strong> registros!</h4>
            <p style="color: #dc3545; font-weight: bold;">Esta ação é IRREVERSÍVEL e os registros serão removidos permanentemente do sistema.</p>
        </div>
        """, unsafe_allow_html=True)
        
        motivo = st.text_area(
            "Motivo da exclusão (opcional, mas recomendado):",
            placeholder="Ex: Registros duplicados, erro em lote, etc...",
            key="motivo_exclusao_massa",
            height=100
        )
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✅ Confirmar Exclusão", type="primary", use_container_width=True):
                with st.spinner(f"Excluindo {quantidade} registros..."):
                    sucessos = 0
                    erros = []
                    
                    for dose_id in ids:
                        # Verificar se o registro ainda existe
                        registro = self.db.fetchone(
                            "SELECT id FROM doses WHERE id = ?",
                            (dose_id,)
                        )
                        
                        if not registro:
                            erros.append(f"Registro ID {dose_id} não encontrado.")
                            continue
                        
                        sucesso, mensagem = self.vacinacao.excluir_registro_vacina(
                            dose_id=dose_id,
                            usuario=st.session_state.usuario_login,
                            motivo=motivo
                        )
                        
                        if sucesso:
                            sucessos += 1
                        else:
                            erros.append(f"ID {dose_id}: {mensagem}")
                    
                    if sucessos > 0:
                        st.success(f"✅ {sucessos} registros excluídos com sucesso!")
                    
                    if erros:
                        with st.expander(f"⚠️ {len(erros)} erros durante a exclusão"):
                            for erro in erros[:20]:
                                st.error(erro)
                            if len(erros) > 20:
                                st.caption(f"... e mais {len(erros) - 20} erros")
                    
                    # Limpar estado
                    del st.session_state.excluir_confirmacao
                    st.session_state.registros_selecionados = []
                    if 'registros_vacinacao' in st.session_state:
                        del st.session_state.registros_vacinacao
                    st.session_state.page_gerenciar = 1
                    st.rerun()
        
        with col2:
            if st.button("❌ Cancelar", use_container_width=True):
                del st.session_state.excluir_confirmacao
                st.rerun()
    
    def _render_estatisticas(self):
        """Renderiza estatísticas de exclusões"""
        st.subheader("📊 Estatísticas de Registros")

        # Total de registros
        total = self.db.fetchone("SELECT COUNT(*) as total FROM doses")
        total_registros = total['total'] if total else 0

        # Registros por usuário
        df_por_usuario = self.db.read_sql("""
            SELECT 
                usuario_registro,
                COUNT(*) as total,
                MIN(data_ap) as primeiro_registro,
                MAX(data_ap) as ultimo_registro
            FROM doses
            WHERE usuario_registro IS NOT NULL
            GROUP BY usuario_registro
            ORDER BY total DESC
        """)

        # Registros por mês
        df_por_mes = self.db.read_sql("""
            SELECT 
                strftime('%Y-%m', data_ap) as mes,
                COUNT(*) as total
            FROM doses
            GROUP BY mes
            ORDER BY mes DESC
            LIMIT 12
        """)

        # Registros por vacina
        df_por_vacina = self.db.read_sql("""
            SELECT 
                vacina,
                COUNT(*) as total
            FROM doses
            GROUP BY vacina
            ORDER BY total DESC
            LIMIT 10
        """)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de Registros", f"{total_registros:,}")

        with col2:
            usuarios_ativos = len(df_por_usuario)
            st.metric("Usuários Registrantes", usuarios_ativos)

        with col3:
            if not df_por_mes.empty:
                media_mensal = df_por_mes['total'].mean()
                st.metric("Média Mensal", f"{media_mensal:.0f}")

        with col4:
            if not df_por_vacina.empty:
                st.metric("Vacinas Diferentes", len(df_por_vacina))

        tab_est1, tab_est2, tab_est3 = st.tabs(["📋 Por Usuário", "📅 Por Mês", "💉 Por Vacina"])

        with tab_est1:
            if not df_por_usuario.empty:
                df_display = df_por_usuario.copy()
                df_display['primeiro_registro'] = pd.to_datetime(df_display['primeiro_registro']).dt.strftime('%d/%m/%Y')
                df_display['ultimo_registro'] = pd.to_datetime(df_display['ultimo_registro']).dt.strftime('%d/%m/%Y')
                
                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "usuario_registro": "Usuário",
                        "total": "Total de Registros",
                        "primeiro_registro": "Primeiro Registro",
                        "ultimo_registro": "Último Registro"
                    }
                )

        with tab_est2:
            if not df_por_mes.empty:
                st.dataframe(
                    df_por_mes,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "mes": "Mês/Ano",
                        "total": "Total de Registros"
                    }
                )

        with tab_est3:
            if not df_por_vacina.empty:
                st.dataframe(
                    df_por_vacina,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "vacina": "Vacina",
                        "total": "Total de Doses"
                    }
                )

        # Logs de exclusão
        with st.expander("📝 Logs de Exclusões (últimos 30 dias)"):
            logs = self.db.read_sql("""
                SELECT 
                    data_hora,
                    usuario,
                    detalhes
                FROM logs
                WHERE acao = 'Excluiu registro de vacinação'
                    AND data_hora >= datetime('now', '-30 days')
                ORDER BY data_hora DESC
                LIMIT 100
            """)

            if not logs.empty:
                logs['data_hora'] = pd.to_datetime(logs['data_hora']).dt.strftime('%d/%m/%Y %H:%M:%S')
                st.dataframe(logs, use_container_width=True, hide_index=True)
                
                # Total de exclusões no período
                st.info(f"Total de exclusões nos últimos 30 dias: {len(logs)}")
            else:
                st.info("Nenhuma exclusão registrada nos últimos 30 dias.")