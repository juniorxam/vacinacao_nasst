"""
vacinacao.py - Página de registro de vacinação
"""

import logging
from datetime import date, timedelta, datetime
from typing import Optional, List, Dict, Any
import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta

from config import CONFIG
from core.security import Security, Formatters
from core.auth_service import AuditLog
from ui.components import UIComponents

logger = logging.getLogger(__name__)


class VacinacaoPage:
    """Página de vacinação"""
    
    def __init__(self, db, vacinacao, servidores, campanhas, auth):
        self.db = db
        self.vacinacao = vacinacao
        self.servidores = servidores
        self.campanhas = campanhas
        self.auth = auth
        self._cache_lotacoes = None
        self._cache_vacinas = None
        self._cache_superintendencias = None
        logger.debug("VacinacaoPage inicializada")
    
    def _get_cached_vacinas(self):
        if self._cache_vacinas is None:
            self._cache_vacinas = self.vacinacao.listar_vacinas_ativas()
        return self._cache_vacinas
    
    def _get_cached_superintendencias(self):
        if self._cache_superintendencias is None:
            from core.estrutura_service import EstruturaOrganizacionalService
            service = EstruturaOrganizacionalService(self.db, None)
            self._cache_superintendencias = service.obter_todas_superintendencias()
        return self._cache_superintendencias
    
    def render(self):
        """Renderiza página de vacinação"""
        st.title("💉 Registrar Vacinação")
        UIComponents.breadcrumb("🏠 Início", "Vacinação")

        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 Individual", 
            "👥 Múltipla", 
            "📁 Em Lote",
            "📄 Importar Meu SUS"
        ])

        with tab1:
            self._render_vacinacao_individual()

        with tab2:
            self._render_vacinacao_multipla()

        with tab3:
            self._render_vacinacao_lote()
        
        with tab4:
            self._render_importar_pdf()
    
    def _buscar_servidor_por_termo(self, termo: str) -> pd.DataFrame:
        """Busca servidores por termo (nome, CPF ou ID)"""
        try:
            return self.db.read_sql(
                """
                SELECT *
                FROM servidores
                WHERE (nome LIKE ? OR cpf LIKE ? OR id_comp LIKE ?)
                  AND situacao_funcional = 'ATIVO'
                LIMIT 10
                """,
                (f"%{termo}%", f"%{termo}%", f"%{termo}%"),
            )
        except Exception as e:
            logger.error(f"Erro na busca de servidor: {e}")
            return pd.DataFrame()
    
    def _exibir_info_servidor(self, servidor: pd.Series):
        """Exibe informações do servidor em colunas"""
        col_info1, col_info2 = st.columns(2)
        
        with col_info1:
            st.markdown(f"**👤 Nome:** {servidor['nome']}")
            st.markdown(f"**📋 CPF:** {Security.formatar_cpf(servidor['cpf'])}")
            st.markdown(f"**🏢 Superintendência:** {servidor.get('superintendencia', 'N/I')}")
            st.markdown(f"**📍 Lotação:** {servidor['lotacao']}")

        with col_info2:
            idade = Formatters.calcular_idade(servidor.get("data_nascimento"))
            st.markdown(f"**🎂 Idade:** {idade or 'N/I'} anos")
            st.markdown(f"**📝 Matrícula:** {servidor['numfunc']}-{servidor['numvinc']}")
            st.markdown(f"**💼 Cargo:** {servidor.get('cargo', 'N/I')}")
            st.markdown(f"**🏠 Local Físico:** {servidor.get('lotacao_fisica', 'N/I')}")
    
    def _render_vacinacao_individual(self):
        """Renderiza formulário individual"""
        UIComponents.create_form_step(1, "Buscar Servidor", active=True)

        col_search1, col_search2 = st.columns([3, 1])
        with col_search1:
            busca = st.text_input(
                "🔍 Buscar servidor:",
                placeholder="Nome, CPF ou matrícula...",
                key="search_vaccine",
                help="Digite para buscar servidores ativos"
            )

        with col_search2:
            st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
            if st.button("🔎 Buscar", use_container_width=True):
                st.session_state.ultima_busca = busca
                logger.debug(f"Busca por servidor: {busca}")

        servidor_selecionado = self._processar_busca_servidor(busca)

        if servidor_selecionado is not None:
            self._render_form_vacinacao(servidor_selecionado)
    
    def _processar_busca_servidor(self, busca: str) -> Optional[pd.Series]:
        """Processa a busca do servidor e retorna o selecionado"""
        termo_busca = busca or st.session_state.get("ultima_busca")
        
        if not termo_busca:
            return None
            
        with UIComponents.show_loading_indicator("Buscando..."):
            df = self._buscar_servidor_por_termo(termo_busca)

        if df.empty:
            UIComponents.show_warning_message("Nenhum servidor encontrado.")
            return None

        options = {
            f"{r['nome']} ({r['lotacao']})": r["id_comp"]
            for _, r in df.iterrows()
        }

        selected = st.radio(
            "Selecione o servidor:",
            list(options.keys()),
            key="select_servidor_vac"
        )

        if selected:
            id_comp = options[selected]
            with st.container():
                st.markdown("---")
                servidor = df[df["id_comp"] == id_comp].iloc[0]
                self._exibir_info_servidor(servidor)
                return servidor
        
        return None
    
    def _get_campanhas_para_select(self) -> tuple[List[str], Dict[str, int]]:
        """Retorna lista de campanhas para selectbox e mapa de IDs"""
        campanhas_df = self.vacinacao.listar_todas_campanhas()
        opcoes = []
        mapa_id = {}
        
        if not campanhas_df.empty:
            for _, row in campanhas_df.iterrows():
                status_icon = {
                    "ATIVA": "🟢",
                    "PLANEJADA": "🟡",
                    "CONCLUÍDA": "🔵",
                    "CANCELADA": "🔴"
                }.get(row['status'], "⚪")
                
                periodo = f"{Formatters.formatar_data_br(row['data_inicio'])} a {Formatters.formatar_data_br(row['data_fim'])}"
                label = f"{status_icon} {row['nome_campanha']} ({row['vacina']}) - {periodo}"
                opcoes.append(label)
                mapa_id[label] = int(row['id'])
        
        return opcoes, mapa_id
    
    def _render_form_vacinacao(self, servidor_selecionado):
        """Renderiza formulário de vacinação"""
        UIComponents.create_form_step(2, "Dados da Vacinação", active=True)

        with st.form("form_vacinacao_individual", clear_on_submit=True):
            confirmar_sem_lote = st.checkbox("Confirmar registro sem número de lote", key="confirm_sem_lote_check")
            
            vacina, dose, lote, data_ap, data_ret, local_ap, via_ap, campanha_id = self._render_campos_vacinacao()
            
            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
            
            with col_btn1:
                submit = st.form_submit_button(
                    "💾 Salvar Vacinação (Ctrl+S)",
                    use_container_width=True,
                    type="primary"
                )

            with col_btn2:
                submit_outra = st.form_submit_button(
                    "➕ Salvar e Nova",
                    use_container_width=True
                )

            with col_btn3:
                if st.form_submit_button("🗑️ Cancelar (Ctrl+Q)", use_container_width=True, type="secondary"):
                    st.session_state.ultima_busca = ""
                    st.rerun()

            if submit or submit_outra:
                self._processar_vacinacao(
                    servidor_selecionado, vacina, dose, data_ap, data_ret, 
                    lote, confirmar_sem_lote, local_ap, via_ap, campanha_id,
                    submit_outra
                )
    
    def _render_campos_vacinacao(self):
        """Renderiza os campos do formulário de vacinação"""
        col_vac1, col_vac2 = st.columns(2)

        with col_vac1:
            vacinas = self._get_cached_vacinas()
            vacina = st.selectbox(
                "Vacina:",
                options=[""] + vacinas + ["➕ Outra"],
                key="vacina_select"
            )

            if vacina == "➕ Outra":
                vacina = st.text_input("Nome da vacina:", key="vacina_outra")

            dose = st.selectbox(
                "Dose:",
                ["1ª Dose", "2ª Dose", "3ª Dose", "Reforço", "Dose Única", "Anual"],
                key="dose_select"
            )

            lote = st.text_input(
                "Nº do Lote:",
                placeholder="Ex: L12345B",
                key="lote_input",
                help="Deixe em branco se não informado"
            )

        with col_vac2:
            data_ap = st.date_input(
                "Data da Aplicação:",
                value=date.today(),
                max_value=date.today(),
                key="data_ap_input"
            )

            data_ret = st.date_input(
                "Data de Retorno:",
                value=self.vacinacao._calcular_data_retorno(vacina if vacina else "", data_ap),
                key="data_ret_input"
            )

            local_ap = st.selectbox(
                "Local:",
                ["NASST Central", "UBS", "Hospital", "Outro"],
                key="local_select"
            )

            via_ap = st.selectbox(
                "Via:",
                ["Intramuscular", "Subcutânea", "Oral", "Intradérmica"],
                key="via_select"
            )

        # Seção de campanhas
        with st.expander("🎯 Associar a Campanha (opcional)"):
            opcoes, mapa_id = self._get_campanhas_para_select()
            campanha_id = None
            
            if opcoes:
                opcao_selecionada = st.selectbox(
                    "Selecione a campanha:",
                    ["Não associar"] + opcoes,
                    key="campanha_select_v2"
                )
                
                if opcao_selecionada != "Não associar":
                    campanha_id = mapa_id.get(opcao_selecionada)
                    self._exibir_info_campanha(mapa_id, opcao_selecionada)
            else:
                st.info("Nenhuma campanha cadastrada.")
        
        return vacina, dose, lote, data_ap, data_ret, local_ap, via_ap, campanha_id
    
    def _exibir_info_campanha(self, mapa_id: Dict, opcao_selecionada: str):
        """Exibe informações da campanha selecionada"""
        try:
            campanha_id = mapa_id.get(opcao_selecionada)
            campanha = self.db.fetchone(
                "SELECT * FROM campanhas WHERE id = ?",
                (campanha_id,)
            )
            if campanha:
                st.info(f"""
                **Campanha:** {campanha['nome_campanha']}
                **Vacina:** {campanha['vacina']}
                **Status:** {campanha['status']}
                **Período:** {Formatters.formatar_data_br(campanha['data_inicio'])} a {Formatters.formatar_data_br(campanha['data_fim'])}
                """)
        except Exception as e:
            logger.error(f"Erro ao exibir info da campanha: {e}")
    
    def _processar_vacinacao(self, servidor, vacina, dose, data_ap, data_ret, 
                            lote, confirmar_sem_lote, local_ap, via_ap, campanha_id, submit_outra):
        """Processa o registro de vacinação"""
        # Prevenção de duplo clique
        if st.session_state.get('vacinacao_submit_lock'):
            st.warning('Aguarde: registro em processamento...')
            return
            
        st.session_state['vacinacao_submit_lock'] = True
        
        try:
            # Validações
            if not vacina or not vacina.strip():
                UIComponents.show_error_message("Informe o nome da vacina!")
                return

            if not lote or not lote.strip():
                if not confirmar_sem_lote:
                    st.warning("⚠️ Lote não informado. Marque a confirmação para continuar.")
                    return
                lote = self.vacinacao.LOTE_NAO_INFORMADO

            # Obter login do usuário
            usuario_login = st.session_state.get('usuario_login', '')
            if not usuario_login:
                usuario_login = st.session_state.get('usuario_nome', '')
                logger.warning(f"Usando nome como login: {usuario_login}")

            # Registrar dose
            inseriu = self.vacinacao.registrar_dose(
                id_comp=str(servidor["id_comp"]),
                vacina=vacina.strip(),
                dose=dose,
                data_ap=data_ap,
                data_ret=data_ret,
                lote=lote.strip(),
                fabricante=None,
                local_aplicacao=local_ap,
                via_aplicacao=via_ap,
                campanha_id=campanha_id,
                usuario=usuario_login,
            )

            if inseriu:
                UIComponents.show_success_message("✅ Vacinação registrada com sucesso!")
                logger.info(f"Vacinação registrada: {servidor['id_comp']} - {vacina}")
            else:
                st.info("ℹ️ Esta vacinação já estava registrada (duplicata ignorada).")

            if submit_outra:
                st.session_state.ultima_busca = ""
                st.rerun()

        except Exception as e:
            logger.error(f"Erro ao registrar vacinação: {e}", exc_info=True)
            UIComponents.show_error_message(f"Erro ao registrar vacinação: {str(e)}")
        
        finally:
            st.session_state['vacinacao_submit_lock'] = False
    
    def _render_vacinacao_multipla(self):
        """Renderiza vacinação múltipla"""
        st.subheader("💉 Vacinação em Massa")

        with st.form("form_vacinacao_multipla"):
            st.info("Selecione um grupo de servidores para vacinação em massa")

            col1, col2 = st.columns(2)
            with col1:
                superintendencia_filtro = st.selectbox(
                    "Filtrar por Superintendência:",
                    ["TODAS"] + self._get_cached_superintendencias(),
                    key="filtro_superintendencia_massa"
                )

            with col2:
                situacao_filtro = st.selectbox(
                    "Situação Funcional:",
                    ["ATIVO", "INATIVO", "TODOS"],
                    key="filtro_situacao_massa"
                )

            vacina = st.selectbox(
                "Vacina a aplicar:",
                self._get_cached_vacinas(),
                key="vacina_massa"
            )

            dose = st.selectbox(
                "Dose:",
                ["1ª Dose", "2ª Dose", "3ª Dose", "Reforço", "Dose Única"],
                key="dose_massa"
            )

            col3, col4 = st.columns(2)
            with col3:
                data_ap = st.date_input(
                    "Data da Aplicação:",
                    value=date.today(),
                    key="data_ap_massa"
                )

            with col4:
                data_ret_default = self.vacinacao._calcular_data_retorno(vacina, data_ap)
                data_ret = st.date_input(
                    "Data de Retorno:",
                    value=data_ret_default,
                    key="data_ret_massa"
                )

            lote = st.text_input(
                "Número do Lote:",
                placeholder="L12345B",
                key="lote_massa"
            )

            if st.form_submit_button("🔍 Buscar Servidores", use_container_width=True):
                self._buscar_servidores_para_massa(superintendencia_filtro, situacao_filtro)

        self._exibir_servidores_massa(vacina, dose, data_ap, data_ret, lote)
    
    def _buscar_servidores_para_massa(self, superintendencia: str, situacao: str):
        """Busca servidores para vacinação em massa"""
        where_clauses = ["situacao_funcional = 'ATIVO'"]
        params = []

        if superintendencia != "TODAS":
            where_clauses.append("superintendencia = ?")
            params.append(superintendencia)

        if situacao != "TODOS":
            where_clauses.append("situacao_funcional = ?")
            params.append(situacao)

        where_sql = " AND ".join(where_clauses)
        query = f"SELECT * FROM servidores WHERE {where_sql} ORDER BY nome LIMIT 100"
        
        servidores = self.db.read_sql(query, params)
        
        if not servidores.empty:
            st.session_state.servidores_massa = servidores
            st.success(f"✅ Encontrados {len(servidores)} servidores")
            logger.info(f"Busca em massa: {len(servidores)} servidores encontrados")
        else:
            st.warning("⚠️ Nenhum servidor encontrado com os filtros selecionados")
    
    def _exibir_servidores_massa(self, vacina: str, dose: str, data_ap: date, 
                                 data_ret: date, lote: str):
        """Exibe lista de servidores para vacinação em massa e botão de ação"""
        if ('servidores_massa' not in st.session_state or 
            st.session_state.servidores_massa is None or 
            st.session_state.servidores_massa.empty):
            return
        
        servidores = st.session_state.servidores_massa
        st.subheader(f"👥 Servidores Selecionados ({len(servidores)})")

        df_preview = servidores[['nome', 'superintendencia', 'lotacao', 'cargo']].head(10)
        st.dataframe(df_preview, use_container_width=True, hide_index=True)

        if len(servidores) > 10:
            st.caption(f"... e mais {len(servidores) - 10} servidores")

        if st.button("💉 Aplicar Vacina a Todos", type="primary", use_container_width=True):
            self._aplicar_vacina_massa(servidores, vacina, dose, data_ap, data_ret, lote)
    
    def _aplicar_vacina_massa(self, servidores: pd.DataFrame, vacina: str, dose: str,
                              data_ap: date, data_ret: date, lote: str):
        """Aplica vacina em massa nos servidores selecionados"""
        with st.spinner("Aplicando vacina em massa..."):
            sucessos = 0
            erros = []
            
            usuario_login = st.session_state.get('usuario_login', '')
            if not usuario_login:
                usuario_login = st.session_state.get('usuario_nome', '')
                logger.warning(f"Usando nome como login em massa: {usuario_login}")

            lote_final = lote if lote.strip() else self.vacinacao.LOTE_NAO_INFORMADO

            for idx, servidor in servidores.iterrows():
                try:
                    sucesso = self.vacinacao.registrar_dose(
                        id_comp=str(servidor["id_comp"]),
                        vacina=vacina,
                        dose=dose,
                        data_ap=data_ap,
                        data_ret=data_ret,
                        lote=lote_final,
                        fabricante=None,
                        local_aplicacao=self.vacinacao.LOCAL_PADRAO,
                        via_aplicacao=self.vacinacao.VIA_PADRAO,
                        campanha_id=None,
                        usuario=usuario_login,
                    )
                    if sucesso:
                        sucessos += 1
                    else:
                        erros.append(f"{servidor['nome']}: já possuía esta dose")
                        
                except Exception as e:
                    logger.error(f"Erro em massa para {servidor['nome']}: {e}")
                    erros.append(f"{servidor['nome']}: {str(e)}")

            # Resultados
            if sucessos > 0:
                UIComponents.show_success_message(f"✅ Vacina aplicada a {sucessos} servidores!")

            if erros:
                with st.expander(f"⚠️ {len(erros)} ocorrências"):
                    for erro in erros[:20]:
                        st.error(erro)
                    if len(erros) > 20:
                        st.caption(f"... e mais {len(erros) - 20}")

            # Registrar no log
            if sucessos > 0:
                audit = AuditLog(self.db)
                audit.registrar(
                    usuario_login,
                    "VACINAÇÃO",
                    "Vacinação em massa",
                    f"{sucessos} doses aplicadas, {len(erros)} falhas"
                )

            del st.session_state.servidores_massa
            st.rerun()
    
    def _render_vacinacao_lote(self):
        """Renderiza vacinação em lote via arquivo"""
        st.subheader("📁 Importar Vacinação em Lote")

        st.info("""
        **Instruções:**
        1. Prepare um arquivo Excel/CSV com as seguintes colunas:
           - `cpf` (obrigatório)
           - `vacina` (obrigatório)
           - `dose` (obrigatório: "1ª Dose", "2ª Dose", etc)
           - `data_aplicacao` (formato: DD/MM/AAAA)
           - `data_retorno` (formato: DD/MM/AAAA) - opcional
           - `lote` (opcional)
           - `local_aplicacao` (opcional)
        2. Faça o upload do arquivo
        3. Confirme os dados
        4. Importe as vacinações
        """)

        uploaded_file = st.file_uploader(
            "Escolha um arquivo (CSV ou Excel)",
            type=["csv", "xlsx", "xls"],
            key="upload_vacinacao_lote"
        )

        if uploaded_file is not None:
            self._processar_arquivo_lote(uploaded_file)
    
    def _processar_arquivo_lote(self, uploaded_file):
        """Processa arquivo de lote de vacinações"""
        try:
            # Carregar arquivo
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.success(f"✅ Arquivo carregado: {len(df)} registros")

            with st.expander("📋 Pré-visualização dos dados"):
                st.dataframe(df.head(10), use_container_width=True)

            # Configurar mapeamento
            config = self._configurar_mapeamento_lote(df)
            
            if config and st.button("🔍 Validar Dados", use_container_width=True):
                self._validar_dados_lote(df, config)
                
        except Exception as e:
            logger.error(f"Erro ao processar arquivo de lote: {e}", exc_info=True)
            st.error(f"❌ Erro ao processar arquivo: {str(e)}")
    
    def _configurar_mapeamento_lote(self, df: pd.DataFrame) -> Optional[Dict]:
        """Configura mapeamento de colunas para importação em lote"""
        colunas_necessarias = ['cpf', 'vacina', 'dose', 'data_aplicacao']
        colunas_faltando = [col for col in colunas_necessarias if col not in df.columns]

        if colunas_faltando:
            st.error(f"❌ Colunas obrigatórias faltando: {', '.join(colunas_faltando)}")
            return None

        st.subheader("⚙️ Configuração da Importação")

        col1, col2 = st.columns(2)
        with col1:
            col_cpf = st.selectbox(
                "Coluna do CPF:",
                df.columns,
                index=df.columns.get_loc('cpf') if 'cpf' in df.columns else 0,
                key="map_cpf"
            )
            col_vacina = st.selectbox(
                "Coluna da Vacina:",
                df.columns,
                index=df.columns.get_loc('vacina') if 'vacina' in df.columns else 0,
                key="map_vacina"
            )

        with col2:
            col_dose = st.selectbox(
                "Coluna da Dose:",
                df.columns,
                index=df.columns.get_loc('dose') if 'dose' in df.columns else 0,
                key="map_dose"
            )
            col_data_ap = st.selectbox(
                "Coluna da Data de Aplicação:",
                df.columns,
                index=df.columns.get_loc('data_aplicacao') if 'data_aplicacao' in df.columns else 0,
                key="map_data_ap"
            )

        col3, col4 = st.columns(2)
        with col3:
            col_data_ret = st.selectbox(
                "Coluna da Data de Retorno:",
                ['Não importar'] + df.columns.tolist(),
                key="map_data_ret"
            )
        with col4:
            col_lote = st.selectbox(
                "Coluna do Lote:",
                ['Não importar'] + df.columns.tolist(),
                key="map_lote"
            )

        return {
            'cpf': col_cpf,
            'vacina': col_vacina,
            'dose': col_dose,
            'data_ap': col_data_ap,
            'data_ret': col_data_ret,
            'lote': col_lote
        }
    
    def _validar_dados_lote(self, df: pd.DataFrame, config: Dict):
        """Valida os dados do arquivo de lote"""
        with st.spinner("Validando dados..."):
            df_processado = df.copy()

            # Validar CPFs
            df_processado['cpf_valido'] = df_processado[config['cpf']].apply(Security.validar_cpf)
            invalid_cpfs = df_processado[~df_processado['cpf_valido']]

            # Validar datas
            try:
                df_processado['data_ap'] = pd.to_datetime(
                    df_processado[config['data_ap']], dayfirst=True, errors='coerce'
                )
                datas_invalidas = df_processado[df_processado['data_ap'].isna()]
            except:
                datas_invalidas = pd.DataFrame()

            # Exibir resultados
            if not invalid_cpfs.empty:
                st.warning(f"⚠️ {len(invalid_cpfs)} CPFs inválidos encontrados")
                with st.expander("Ver CPFs inválidos"):
                    st.dataframe(invalid_cpfs[[config['cpf'], config['vacina']]], use_container_width=True)

            if not datas_invalidas.empty:
                st.warning(f"⚠️ {len(datas_invalidas)} datas inválidas encontradas")

            if invalid_cpfs.empty and datas_invalidas.empty:
                st.success("✅ Todos os dados são válidos!")
                
                # Preparar dados para importação
                if config['data_ret'] == 'Não importar':
                    df_processado['data_ret'] = df_processado['data_ap'] + pd.Timedelta(days=30)
                else:
                    df_processado['data_ret'] = pd.to_datetime(
                        df_processado[config['data_ret']], dayfirst=True, errors='coerce'
                    )

                st.session_state.dados_vacinacao_processados = df_processado
                st.session_state.config_lote = config
                st.rerun()

        # Se já processou, mostrar botão de importação
        if 'dados_vacinacao_processados' in st.session_state:
            self._exibir_importacao_lote()
    
    def _exibir_importacao_lote(self):
        """Exibe botão para importar dados validados"""
        df = st.session_state.dados_vacinacao_processados
        config = st.session_state.config_lote
        
        st.subheader("🚀 Importar Vacinações")
        st.info(f"Pronto para importar {len(df)} vacinações")

        if st.button("💾 Importar Todos", type="primary", use_container_width=True):
            self._executar_importacao_lote(df, config)
    
    def _executar_importacao_lote(self, df: pd.DataFrame, config: Dict):
        """Executa a importação em lote"""
        with st.spinner(f"Importando {len(df)} vacinações..."):
            sucessos = 0
            erros = []
            
            usuario_login = st.session_state.get('usuario_login', '')
            if not usuario_login:
                usuario_login = st.session_state.get('usuario_nome', '')
                logger.warning(f"Usando nome como login em lote: {usuario_login}")

            for idx, row in df.iterrows():
                try:
                    cpf_limpo = Security.clean_cpf(row[config['cpf']])
                    servidor = self.db.fetchone(
                        "SELECT id_comp FROM servidores WHERE cpf = ?",
                        (cpf_limpo,)
                    )

                    if servidor:
                        data_ret = None
                        if pd.notna(row.get('data_ret')):
                            data_ret = row['data_ret'].date()
                        
                        sucesso = self.vacinacao.registrar_dose(
                            id_comp=str(servidor["id_comp"]),
                            vacina=str(row[config['vacina']]),
                            dose=str(row[config['dose']]),
                            data_ap=row['data_ap'].date(),
                            data_ret=data_ret,
                            lote=str(row[config['lote']]) if config['lote'] != 'Não importar' and pd.notna(row[config['lote']]) else None,
                            fabricante=None,
                            local_aplicacao=self.vacinacao.LOCAL_PADRAO,
                            via_aplicacao=self.vacinacao.VIA_PADRAO,
                            campanha_id=None,
                            usuario=usuario_login,
                        )
                        
                        if sucesso:
                            sucessos += 1
                        # Se não sucesso, é duplicata - não conta como erro
                        
                    else:
                        erros.append(f"CPF {cpf_limpo}: Servidor não encontrado")

                except Exception as e:
                    logger.error(f"Erro na importação lote linha {idx+2}: {e}")
                    erros.append(f"Linha {idx+2}: {str(e)}")

            # Resultados
            if sucessos > 0:
                UIComponents.show_success_message(f"✅ {sucessos} vacinações importadas!")
                
                audit = AuditLog(self.db)
                audit.registrar(
                    usuario_login,
                    "VACINAÇÃO",
                    "Importação em lote",
                    f"{sucessos} vacinações importadas"
                )

            if erros:
                with st.expander(f"⚠️ {len(erros)} erros encontrados"):
                    for erro in erros[:20]:
                        st.error(erro)
                    if len(erros) > 20:
                        st.caption(f"... e mais {len(erros) - 20} erros")

            # Limpar estado
            del st.session_state.dados_vacinacao_processados
            del st.session_state.config_lote
            st.rerun()
    
    def _render_importar_pdf(self):
        """Renderiza importação a partir do PDF da Carteira Nacional de Vacinação Digital"""
        st.subheader("📄 Importar do Meu SUS Digital")
        st.markdown("""
        Faça o upload do arquivo PDF da **Carteira Nacional de Vacinação Digital**.
        O sistema tentará extrair automaticamente os dados e importar os registros de vacinação.
        """)
        
        uploaded_pdf = st.file_uploader(
            "Selecione o arquivo PDF",
            type=["pdf"],
            key="upload_pdf_vacinas"
        )
        
        if uploaded_pdf is not None:
            self._processar_pdf_sus(uploaded_pdf)
    
    def _processar_pdf_sus(self, uploaded_pdf):
        """Processa PDF do Meu SUS Digital"""
        with st.spinner("Processando PDF..."):
            try:
                dados_titular = self.vacinacao.extrair_dados_titular_pdf(uploaded_pdf)
                vacinas_extraidas = self.vacinacao.extrair_vacinas_pdf(uploaded_pdf)
                
                if not vacinas_extraidas:
                    st.warning("Nenhum registro de vacinação encontrado no PDF.")
                    return
                
                st.success(f"✅ {len(vacinas_extraidas)} registros encontrados no PDF.")
                
                # Exibir dados do titular
                if dados_titular.get('nome') or dados_titular.get('cpf'):
                    with st.expander("👤 Dados do Titular Identificados"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.text_input("Nome", value=dados_titular.get('nome', ''), disabled=True)
                        with col2:
                            st.text_input("CPF", value=dados_titular.get('cpf', ''), disabled=True)
                        with col3:
                            st.text_input("Data Nascimento", value=dados_titular.get('data_nascimento', ''), disabled=True)
                
                # Mostrar prévia
                df_preview = pd.DataFrame(vacinas_extraidas)
                st.dataframe(df_preview, use_container_width=True)
                
                # Selecionar registros
                indices_selecionados = st.multiselect(
                    "Selecione os registros para importar:",
                    options=range(len(vacinas_extraidas)),
                    format_func=lambda i: f"{vacinas_extraidas[i]['vacina']} - {vacinas_extraidas[i]['data']} ({vacinas_extraidas[i]['dose']})",
                    default=list(range(len(vacinas_extraidas))),
                    key="select_vacinas_pdf"
                )
                
                if indices_selecionados:
                    self._importar_registros_pdf(vacinas_extraidas, indices_selecionados, dados_titular)
                    
            except Exception as e:
                logger.error(f"Erro ao processar PDF: {e}", exc_info=True)
                st.error(f"❌ Erro ao processar PDF: {str(e)}")
    
    def _importar_registros_pdf(self, vacinas_extraidas: List[Dict], 
                                indices_selecionados: List[int], dados_titular: Dict):
        """Importa registros selecionados do PDF"""
        
        # Identificar servidor
        servidor_encontrado = self._identificar_servidor_pdf(dados_titular)
        
        if not servidor_encontrado:
            st.warning("⚠️ Servidor não identificado automaticamente. Selecione manualmente:")
            servidor_encontrado = self._selecionar_servidor_manual()
        
        if not servidor_encontrado:
            st.error("❌ É necessário associar os registros a um servidor.")
            return
        
        # Verificar duplicatas
        novas, existentes = self._verificar_duplicatas_pdf(
            [vacinas_extraidas[i] for i in indices_selecionados], 
            servidor_encontrado
        )
        
        # Botão de importação
        if novas and st.button("📥 Importar Registros", type="primary", use_container_width=True):
            self._executar_importacao_pdf(novas, servidor_encontrado, len(existentes))
    
    def _identificar_servidor_pdf(self, dados_titular: Dict) -> Optional[Dict]:
        """Tenta identificar servidor pelos dados do PDF"""
        if dados_titular.get('cpf'):
            cpf_limpo = Security.clean_cpf(dados_titular['cpf'])
            servidor = self.db.fetchone(
                "SELECT id_comp, nome FROM servidores WHERE cpf = ?",
                (cpf_limpo,)
            )
            if servidor:
                st.success(f"✅ Servidor identificado: **{servidor['nome']}**")
                return {'id_comp': servidor['id_comp'], 'nome': servidor['nome']}
        return None
    
    def _selecionar_servidor_manual(self) -> Optional[Dict]:
        """Permite seleção manual do servidor"""
        busca_servidor = st.text_input(
            "Buscar servidor por nome ou CPF:",
            placeholder="Digite para buscar...",
            key="busca_servidor_pdf"
        )
        
        if busca_servidor:
            servidores = self.servidores.buscar_servidores(busca_servidor, limit=10)
            if not servidores.empty:
                opcoes = {}
                for _, row in servidores.iterrows():
                    cpf_formatado = Security.formatar_cpf(row['cpf'])
                    opcoes[f"{row['nome']} ({cpf_formatado})"] = {
                        'id_comp': row['id_comp'],
                        'nome': row['nome']
                    }
                
                selecionado = st.selectbox(
                    "Selecione o servidor:",
                    list(opcoes.keys()),
                    key="select_servidor_pdf_manual"
                )
                return opcoes.get(selecionado)
        return None
    
    def _verificar_duplicatas_pdf(self, vacinas: List[Dict], servidor: Dict) -> tuple[List, List]:
        """Verifica quais vacinas do PDF já existem no banco"""
        novas = []
        existentes = []
        
        for vacina in vacinas:
            try:
                data_ap = datetime.strptime(vacina['data'], '%d/%m/%Y').date()
                
                existe = self.db.fetchone(
                    """
                    SELECT id FROM doses 
                    WHERE id_comp = ? AND vacina = ? AND dose = ? AND data_ap = ?
                    """,
                    (servidor['id_comp'], vacina['vacina'], vacina['dose'], data_ap.isoformat())
                )
                
                if existe:
                    existentes.append(vacina)
                else:
                    novas.append(vacina)
            except Exception as e:
                logger.error(f"Erro ao verificar duplicata: {e}")
                novas.append(vacina)  # Assume nova em caso de erro
        
        # Mostrar resultado
        col1, col2 = st.columns(2)
        with col1:
            st.metric("✅ Vacinas Novas", len(novas))
        with col2:
            st.metric("⚠️ Já existentes", len(existentes))
        
        if existentes:
            st.info(f"{len(existentes)} registros já existem e serão ignorados.")
        
        return novas, existentes
    
    def _executar_importacao_pdf(self, vacinas: List[Dict], servidor: Dict, duplicados: int):
        """Executa a importação dos registros do PDF"""
        usuario_login = st.session_state.get('usuario_login', '')
        if not usuario_login:
            usuario_login = st.session_state.get('usuario_nome', '')
        
        sucessos = 0
        erros = []
        
        for dados in vacinas:
            try:
                data_ap = datetime.strptime(dados['data'], '%d/%m/%Y').date()
                
                sucesso = self.vacinacao.registrar_dose(
                    id_comp=servidor['id_comp'],
                    vacina=dados['vacina'],
                    dose=dados['dose'],
                    data_ap=data_ap,
                    data_ret=self.vacinacao._calcular_data_retorno(dados['vacina'], data_ap),
                    lote=dados['lote'] if dados['lote'] and dados['lote'].strip() else self.vacinacao.LOTE_NAO_INFORMADO,
                    fabricante=None,
                    local_aplicacao=self.vacinacao.IMPORTADO_SUS,
                    via_aplicacao=self.vacinacao.VIA_PADRAO,
                    campanha_id=None,
                    usuario=usuario_login
                )
                
                if sucesso:
                    sucessos += 1
                    
            except Exception as e:
                logger.error(f"Erro ao importar {dados['vacina']}: {e}")
                erros.append(f"{dados['vacina']}: {str(e)}")
        
        # Resultados
        if sucessos > 0:
            st.success(f"✅ {sucessos} novos registros importados para {servidor['nome']}!")
        
        if erros:
            with st.expander(f"⚠️ {len(erros)} erros"):
                for erro in erros[:10]:
                    st.error(erro)
        
        # Registrar log
        if sucessos > 0:
            audit = AuditLog(self.db)
            audit.registrar(
                usuario_login,
                "VACINAÇÃO",
                "Importação PDF Meu SUS",
                f"{sucessos} novos registros para {servidor['id_comp']} ({duplicados} duplicados)"
            )