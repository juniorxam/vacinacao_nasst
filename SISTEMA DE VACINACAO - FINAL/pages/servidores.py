"""
servidores.py - Página de gerenciamento de servidores
Versão refatorada usando ImportadorServidores
"""

import io
from datetime import date

import pandas as pd
import streamlit as st

from config import CONFIG
from core.security import Security, Formatters
from ui.components import UIComponents
from ui.importador import ImportadorServidores


class ServidoresPage:
    """Página de gerenciamento de servidores"""
    
    def __init__(self, db, servidores, auth, estrutura_service=None):
        self.db = db
        self.servidores = servidores
        self.auth = auth
        self.estrutura_service = estrutura_service
        
        # Cache
        self._cache_lotacoes = None
        self._cache_cargos = None
        self._cache_superintendencias = None
    
    def _get_cached_lotacoes(self):
        if self._cache_lotacoes is None:
            self._cache_lotacoes = self.servidores.obter_lotacoes()
        return self._cache_lotacoes
    
    def _get_cached_cargos(self):
        if self._cache_cargos is None:
            self._cache_cargos = self.servidores.obter_cargos_existentes()
        return self._cache_cargos
    
    def _get_cached_superintendencias(self):
        if self._cache_superintendencias is None:
            self._cache_superintendencias = self.servidores.obter_superintendencias()
        return self._cache_superintendencias
    
    def render(self):
        """Renderiza página de servidores"""
        st.title("👥 Gerenciar Servidores")
        UIComponents.breadcrumb("🏠 Início", "Servidores")

        tab1, tab2, tab3, tab4 = st.tabs([
            "🔍 Consultar", "➕ Cadastrar", "📥 Importar", "⚙️ Administrar"
        ])

        with tab1:
            self._render_consultar()

        with tab2:
            self._render_cadastrar()

        with tab3:
            self._render_importar()

        with tab4:
            self._render_administrar()
    
    def _render_consultar(self):
        """Renderiza consulta de servidores"""
        st.subheader("🔍 Consultar Servidores")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            filtro_nome = st.text_input("Nome:", key="filtro_nome")

        with col2:
            filtro_superintendencia = st.selectbox(
                "Superintendência:",
                ["TODAS"] + self._get_cached_superintendencias(),
                key="filtro_superintendencia"
            )

        with col3:
            filtro_lotacao = st.selectbox(
                "Lotação:",
                ["TODAS"] + self._get_cached_lotacoes(),
                key="filtro_lotacao"
            )

        with col4:
            filtro_situacao = st.selectbox(
                "Situação:",
                ["TODOS", "ATIVO", "INATIVO"],
                key="filtro_situacao"
            )

        if st.button("🔎 Buscar", use_container_width=True):
            self._executar_busca(filtro_nome, filtro_superintendencia, 
                                 filtro_lotacao, filtro_situacao)

        self._exibir_resultados_busca()
    
    def _executar_busca(self, nome, superintendencia, lotacao, situacao):
        """Executa a busca com os filtros fornecidos"""
        where_clauses = []
        params = []

        if nome:
            where_clauses.append("nome LIKE ?")
            params.append(f"%{nome}%")

        if superintendencia != "TODAS":
            where_clauses.append("superintendencia = ?")
            params.append(superintendencia)

        if lotacao != "TODAS":
            where_clauses.append("lotacao = ?")
            params.append(lotacao)

        if situacao != "TODOS":
            where_clauses.append("situacao_funcional = ?")
            params.append(situacao)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            SELECT id_comp, nome, cpf, superintendencia, lotacao, lotacao_fisica, 
                   cargo, situacao_funcional, data_nascimento, data_admissao
            FROM servidores
            WHERE {where_sql}
            ORDER BY nome
            LIMIT 100
        """

        servidores = self.db.read_sql(query, params)
        st.session_state.servidores_filtrados = servidores
    
    def _exibir_resultados_busca(self):
        """Exibe os resultados da busca"""
        if 'servidores_filtrados' not in st.session_state or st.session_state.servidores_filtrados is None:
            return
        
        servidores = st.session_state.servidores_filtrados

        if servidores.empty:
            st.info("Nenhum servidor encontrado com os filtros selecionados.")
            return

        st.subheader(f"📊 Resultados: {len(servidores)} servidores")

        # Preparar dados para exibição
        df_display = servidores.copy()
        df_display['cpf'] = df_display['cpf'].apply(Security.formatar_cpf)
        df_display['data_nascimento'] = df_display['data_nascimento'].apply(Formatters.formatar_data_br)
        df_display['data_admissao'] = df_display['data_admissao'].apply(Formatters.formatar_data_br)
        df_display['superintendencia'] = df_display['superintendencia'].fillna('Não informado')
        df_display['lotacao_fisica'] = df_display['lotacao_fisica'].fillna('Não informado')

        df_display = df_display.rename(columns={
            'id_comp': 'ID',
            'nome': 'Nome',
            'cpf': 'CPF',
            'superintendencia': 'Superintendência',
            'lotacao': 'Lotação',
            'lotacao_fisica': 'Local Físico',
            'cargo': 'Cargo',
            'situacao_funcional': 'Situação',
            'data_nascimento': 'Nascimento',
            'data_admissao': 'Admissão'
        })

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.TextColumn("ID", width="small"),
                "Nome": st.column_config.TextColumn("Nome", width="large"),
                "CPF": st.column_config.TextColumn("CPF", width="medium"),
                "Superintendência": st.column_config.TextColumn("Superintendência", width="medium"),
                "Lotação": st.column_config.TextColumn("Lotação", width="medium"),
                "Local Físico": st.column_config.TextColumn("Local Físico", width="medium"),
                "Cargo": st.column_config.TextColumn("Cargo", width="medium"),
                "Situação": st.column_config.TextColumn("Situação", width="small"),
            }
        )

        self._render_botoes_exportacao(servidores)
        self._render_estatisticas(servidores)
    
    def _render_botoes_exportacao(self, servidores):
        """Renderiza botões de exportação"""
        col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 2])

        with col_exp1:
            csv = servidores.to_csv(index=False)
            st.download_button(
                "📥 CSV",
                csv,
                "servidores.csv",
                "text/csv",
                use_container_width=True
            )

        with col_exp2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                servidores.to_excel(writer, index=False, sheet_name='Servidores')

            st.download_button(
                "📊 Excel",
                excel_buffer.getvalue(),
                "servidores.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    def _render_estatisticas(self, servidores):
        """Renderiza estatísticas rápidas"""
        with st.expander("📈 Estatísticas Rápidas"):
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

            with col_stat1:
                ativos = len(servidores[servidores['situacao_funcional'] == 'ATIVO'])
                st.metric("Ativos", ativos)

            with col_stat2:
                inativos = len(servidores[servidores['situacao_funcional'] == 'INATIVO'])
                st.metric("Inativos", inativos)

            with col_stat3:
                superintendencias = servidores['superintendencia'].nunique()
                st.metric("Superintendências", superintendencias)

            with col_stat4:
                lotacoes = servidores['lotacao'].nunique()
                st.metric("Lotações", lotacoes)
    
    def _render_cadastrar(self):
        """Renderiza cadastro individual"""
        st.subheader("➕ Cadastrar Servidor Individual")

        with st.form("form_cadastro_servidor", clear_on_submit=True):
            st.markdown("### 👤 Dados Pessoais")
            col1, col2 = st.columns(2)

            with col1:
                nome = st.text_input(
                    "Nome Completo:*",
                    placeholder="Ex: MARIA DA SILVA SANTOS",
                    key="cad_nome"
                )

                cpf = st.text_input(
                    "CPF:*",
                    placeholder="000.000.000-00",
                    key="cad_cpf"
                )

                data_nascimento = st.date_input(
                    "Data de Nascimento:",
                    max_value=date.today(),
                    key="cad_nascimento"
                )

                sexo = st.selectbox(
                    "Sexo:",
                    ["", "MASCULINO", "FEMININO"],
                    key="cad_sexo"
                )

            with col2:
                telefone = st.text_input(
                    "Telefone:",
                    placeholder="(00) 00000-0000",
                    key="cad_telefone"
                )

                email = st.text_input(
                    "E-mail:",
                    placeholder="exemplo@dominio.com",
                    key="cad_email"
                )

            st.markdown("### 💼 Dados Funcionais")
            col3, col4 = st.columns(2)

            with col3:
                matricula_auto = self.servidores.gerar_matricula_automatica()
                numfunc = st.text_input(
                    "Número Funcional:*",
                    value=matricula_auto,
                    key="cad_numfunc"
                )

                numvinc = st.text_input(
                    "Número de Vínculo:*",
                    value="1",
                    key="cad_numvinc"
                )

                superintendencia = st.selectbox(
                    "Superintendência:*",
                    [""] + self._get_cached_superintendencias(),
                    key="cad_superintendencia"
                )

                if superintendencia == "":
                    superintendencia = st.text_input(
                        "Nova Superintendência:",
                        placeholder="Digite o nome",
                        key="cad_nova_superintendencia"
                    )

            with col4:
                setores = []
                if superintendencia and superintendencia not in ["", "Nova Superintendência:"]:
                    if self.estrutura_service:
                        setores = self.estrutura_service.obter_setores_por_superintendencia(superintendencia)

                lotacao = st.selectbox(
                    "Setor/Lotação:*",
                    [""] + setores,
                    key="cad_lotacao",
                    disabled=not superintendencia
                )

                if lotacao == "":
                    lotacao = st.text_input(
                        "Novo Setor/Lotação:",
                        placeholder="Digite o nome do setor",
                        key="cad_nova_lotacao"
                    )

                cargo = st.selectbox(
                    "Cargo:",
                    [""] + self._get_cached_cargos(),
                    key="cad_cargo"
                )

                if cargo == "":
                    cargo = st.text_input(
                        "Novo Cargo:",
                        placeholder="Digite um novo cargo",
                        key="cad_novo_cargo"
                    )

            # Local Físico
            lotacao_fisica = None
            if lotacao and self.estrutura_service:
                lotacao_fisica = self.estrutura_service.obter_local_fisico_por_setor(lotacao)
                if lotacao_fisica:
                    st.info(f"📍 **Local Físico:** {lotacao_fisica}")
                else:
                    lotacao_fisica = st.text_input(
                        "Local Físico:",
                        placeholder="Digite o local físico",
                        key="cad_lotacao_fisica"
                    )
            else:
                lotacao_fisica = st.text_input(
                    "Local Físico:",
                    placeholder="Digite o local físico",
                    key="cad_lotacao_fisica"
                )

            col5, col6 = st.columns(2)

            with col5:
                tipo_vinculo = st.selectbox(
                    "Tipo de Vínculo:",
                    ["", "EFETIVO", "COMISSIONADO", "TEMPORÁRIO", "TERCEIRIZADO"],
                    key="cad_tipo_vinculo"
                )

            with col6:
                situacao_funcional = st.selectbox(
                    "Situação Funcional:",
                    ["ATIVO", "INATIVO"],
                    key="cad_situacao"
                )

            data_admissao = st.date_input(
                "Data de Admissão:",
                max_value=date.today(),
                key="cad_admissao"
            )

            st.markdown("*Campos obrigatórios")

            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

            with col_btn1:
                submit = st.form_submit_button(
                    "💾 Salvar Servidor",
                    use_container_width=True,
                    type="primary"
                )

            with col_btn2:
                submit_novo = st.form_submit_button(
                    "➕ Salvar e Novo",
                    use_container_width=True
                )

            with col_btn3:
                st.form_submit_button(
                    "🗑️ Cancelar",
                    use_container_width=True,
                    type="secondary"
                )

            if submit or submit_novo:
                self._processar_cadastro(
                    nome, cpf, numfunc, numvinc, superintendencia, lotacao,
                    cargo, lotacao_fisica, data_nascimento, sexo, telefone, email,
                    data_admissao, tipo_vinculo, situacao_funcional, submit_novo
                )
    
    def _processar_cadastro(self, nome, cpf, numfunc, numvinc, superintendencia, lotacao,
                           cargo, lotacao_fisica, data_nascimento, sexo, telefone, email,
                           data_admissao, tipo_vinculo, situacao_funcional, submit_novo):
        """Processa cadastro de servidor"""
        # Validações
        if not nome.strip():
            st.error("❌ Nome é obrigatório!")
            return

        if not cpf.strip():
            st.error("❌ CPF é obrigatório!")
            return

        if not Security.validar_cpf(cpf):
            st.error("❌ CPF inválido!")
            return

        if not superintendencia.strip():
            st.error("❌ Superintendência é obrigatória!")
            return

        if not lotacao.strip():
            st.error("❌ Lotação é obrigatória!")
            return

        if not numfunc.strip():
            st.error("❌ Número funcional é obrigatório!")
            return

        dados = {
            "numfunc": numfunc.strip(),
            "numvinc": numvinc.strip() or "1",
            "nome": nome.strip().upper(),
            "cpf": cpf,
            "data_nascimento": data_nascimento.isoformat() if data_nascimento else None,
            "sexo": sexo,
            "cargo": cargo.strip().upper() if cargo else None,
            "lotacao": lotacao.strip().upper(),
            "lotacao_fisica": lotacao_fisica.strip().upper() if lotacao_fisica else None,
            "superintendencia": superintendencia.strip().upper(),
            "telefone": telefone.strip() if telefone else None,
            "email": email.strip().lower() if email else None,
            "data_admissao": data_admissao.isoformat() if data_admissao else None,
            "tipo_vinculo": tipo_vinculo,
            "situacao_funcional": situacao_funcional,
        }

        sucesso, mensagem = self.servidores.cadastrar_individual(
            dados,
            st.session_state.usuario_nome
        )

        if sucesso:
            st.success(f"✅ {mensagem}")
            if submit_novo:
                st.rerun()
        else:
            st.error(f"❌ {mensagem}")
    
    def _render_importar(self):
        """Renderiza importação em lote usando o componente refatorado"""
        importador = ImportadorServidores(self.servidores, self.db)
        importador.render()
    
    def _render_administrar(self):
        """Renderiza administração de servidores"""
        st.subheader("⚙️ Administrar Servidores")

        if not self.auth.verificar_permissoes(st.session_state.nivel_acesso, "ADMIN"):
            st.error("❌ Acesso não autorizado. Apenas administradores podem acessar esta funcionalidade.")
            return

        st.markdown("### 🗑️ Excluir Servidor")
        st.warning("**Atenção:** Esta ação é irreversível e excluirá também o histórico de vacinação do servidor.")

        busca_exclusao = st.text_input(
            "Buscar servidor para exclusão:",
            placeholder="Nome, CPF ou matrícula",
            key="busca_exclusao"
        )

        if busca_exclusao:
            with st.spinner("Buscando..."):
                servidores = self.servidores.buscar_servidores(busca_exclusao, limit=5)

                if servidores is not None and not servidores.empty:
                    for _, servidor in servidores.iterrows():
                        with st.container():
                            col_info, col_action = st.columns([3, 1])

                            with col_info:
                                st.markdown(f"""
                                **Nome:** {servidor['nome']}
                                **CPF:** {Security.formatar_cpf(servidor['cpf'])}
                                **Superintendência:** {servidor.get('superintendencia', 'N/I')}
                                **Lotação:** {servidor['lotacao']}
                                **Matrícula:** {servidor['numfunc']}-{servidor['numvinc']}
                                """)

                            with col_action:
                                if st.button("🗑️ Excluir", key=f"del_{servidor['id_comp']}", type="secondary"):
                                    st.warning(f"Tem certeza que deseja excluir {servidor['nome']}?")
                                    col_conf1, col_conf2 = st.columns(2)

                                    with col_conf1:
                                        if st.button("✅ Sim, excluir", key=f"confirm_del_{servidor['id_comp']}"):
                                            try:
                                                self.servidores.excluir_servidor(
                                                    str(servidor['id_comp']),
                                                    st.session_state.usuario_nome
                                                )
                                                st.success("✅ Servidor excluído com sucesso!")
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"❌ Erro ao excluir: {str(e)}")

                                    with col_conf2:
                                        if st.button("❌ Cancelar", key=f"cancel_del_{servidor['id_comp']}"):
                                            st.rerun()
                else:
                    st.info("Nenhum servidor encontrado.")