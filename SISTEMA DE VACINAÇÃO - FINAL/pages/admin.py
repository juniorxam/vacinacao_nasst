"""
admin.py - Página de administração do sistema com monitoramento
"""

import os
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from config import CONFIG
from core.security import Security
from core.auth_service import AuditLog
from ui.components import UIComponents
from core.backup import BackupManager, BackupScheduler


class AdminPage:
    """Página de administração com monitoramento"""
    
    def __init__(self, db, auth, servidores):
        self.db = db
        self.auth = auth
        self.servidores = servidores
    
    def render(self):
        """Renderiza página de administração"""
        st.title("⚙️ Administração do Sistema")
        UIComponents.breadcrumb("🏠 Início", "Administração")

        if not self.auth.verificar_permissoes(st.session_state.nivel_acesso, "ADMIN"):
            st.error("❌ Apenas administradores podem acessar esta página.")
            return

        # Abas da administração (agora com 7 abas)
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "👥 Usuários", 
            "💉 Vacinas", 
            "🛠️ Utilitários", 
            "📊 Sistema", 
            "🔐 Gerenciar Usuários",
            "💾 Backup Automático",
            "📈 Monitoramento"
        ])

        with tab1:
            self._render_usuarios()

        with tab2:
            self._render_vacinas()

        with tab3:
            self._render_utilitarios()

        with tab4:
            self._render_sistema()

        with tab5:
            self._render_gerenciar_usuarios()

        with tab6:
            self._render_backup()

        with tab7:
            self._render_monitoramento()
    
    def _render_usuarios(self):
        """Renderiza administração de usuários (visão geral)"""
        st.subheader("👥 Visão Geral de Usuários")

        usuarios = self.db.read_sql(
            "SELECT login, nome, nivel_acesso, lotacao_permitida, ativo, data_criacao FROM usuarios ORDER BY nome"
        )

        if not usuarios.empty:
            st.success(f"✅ {len(usuarios)} usuários cadastrados")

            df_usuarios = usuarios.copy()
            df_usuarios['data_criacao'] = pd.to_datetime(df_usuarios['data_criacao']).dt.strftime('%d/%m/%Y')

            st.dataframe(
                df_usuarios,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "login": "Login",
                    "nome": "Nome",
                    "nivel_acesso": "Nível",
                    "lotacao_permitida": "Lotação Permitida",
                    "ativo": "Ativo",
                    "data_criacao": "Data Criação"
                }
            )

        st.subheader("➕ Novo Usuário")

        with st.form("form_novo_usuario"):
            col1, col2 = st.columns(2)

            with col1:
                login = st.text_input("Login:", key="novo_usuario_login")
                nome = st.text_input("Nome:", key="novo_usuario_nome")
                senha = st.text_input("Senha:", type="password", key="novo_usuario_senha")

            with col2:
                nivel_acesso = st.selectbox(
                    "Nível de Acesso:",
                    ["VISUALIZADOR", "OPERADOR", "ADMIN"],
                    key="novo_usuario_nivel"
                )

                lotacao_permitida = st.selectbox(
                    "Lotação Permitida:",
                    ["TODOS"] + self.servidores.obter_lotacoes(),
                    key="novo_usuario_lotacao"
                )

                ativo = st.checkbox("Ativo", value=True, key="novo_usuario_ativo")

            if st.form_submit_button("💾 Criar Usuário", use_container_width=True):
                self._processar_criacao_usuario(login, nome, senha, nivel_acesso, lotacao_permitida, ativo)
    
    def _processar_criacao_usuario(self, login, nome, senha, nivel, lotacao, ativo):
        """Processa criação de novo usuário"""
        if not login.strip():
            st.error("❌ Login é obrigatório!")
            return

        if not nome.strip():
            st.error("❌ Nome é obrigatório!")
            return

        if not senha.strip():
            st.error("❌ Senha é obrigatória!")
            return

        if len(senha) < 6:
            st.error("❌ Senha deve ter pelo menos 6 caracteres!")
            return

        existe = self.db.fetchone("SELECT login FROM usuarios WHERE login = ?", (login.strip(),))
        if existe:
            st.error("❌ Login já existe!")
            return

        try:
            senha_hash = Security.sha256_hex(senha)
            self.db.execute(
                """
                INSERT INTO usuarios (login, senha, nome, nivel_acesso, lotacao_permitida, ativo)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (login.strip(), senha_hash, nome.strip(), nivel, lotacao, 1 if ativo else 0)
            )

            audit = AuditLog(self.db)
            audit.registrar(
                st.session_state.usuario_nome,
                "ADMIN",
                "Criou usuário",
                f"Novo usuário: {login}"
            )

            st.success("✅ Usuário criado com sucesso!")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Erro ao criar usuário: {str(e)}")
    
    def _render_gerenciar_usuarios(self):
        """Renderiza gerenciamento completo de usuários"""
        st.subheader("🔐 Gerenciar Usuários")
        
        usuarios = self.db.read_sql(
            "SELECT login, nome, nivel_acesso, lotacao_permitida, ativo, data_criacao FROM usuarios ORDER BY nome"
        )
        
        if usuarios.empty:
            st.info("Nenhum usuário cadastrado.")
            return
        
        usuarios_lista = usuarios['nome'].tolist()
        usuario_selecionado = st.selectbox(
            "Selecione um usuário para gerenciar:",
            usuarios_lista,
            key="select_usuario_gerenciar"
        )
        
        if usuario_selecionado:
            usuario_data = usuarios[usuarios['nome'] == usuario_selecionado].iloc[0]
            login = usuario_data['login']
            
            st.markdown("---")
            st.subheader(f"📝 Editando: {usuario_selecionado}")
            
            tab_edit, tab_password, tab_status = st.tabs(["✏️ Editar Dados", "🔑 Resetar Senha", "🔄 Status"])
            
            with tab_edit:
                self._render_editar_usuario(login, usuario_data)
            
            with tab_password:
                self._render_resetar_senha(login, usuario_selecionado)
            
            with tab_status:
                self._render_alterar_status(login, usuario_data)
    
    def _render_editar_usuario(self, login, usuario_data):
        """Editar dados do usuário"""
        with st.form(f"form_editar_usuario_{login}"):
            st.markdown("### ✏️ Editar Dados do Usuário")
            
            col1, col2 = st.columns(2)
            
            with col1:
                novo_nome = st.text_input(
                    "Nome:",
                    value=usuario_data['nome'],
                    key=f"edit_nome_{login}"
                )
                
                novo_login = st.text_input(
                    "Login:",
                    value=login,
                    disabled=True,
                    key=f"edit_login_{login}"
                )
                st.caption("⚠️ O login não pode ser alterado")
            
            with col2:
                novo_nivel = st.selectbox(
                    "Nível de Acesso:",
                    ["VISUALIZADOR", "OPERADOR", "ADMIN"],
                    index=["VISUALIZADOR", "OPERADOR", "ADMIN"].index(usuario_data['nivel_acesso']),
                    key=f"edit_nivel_{login}"
                )
                
                lotacoes = ["TODOS"] + self.servidores.obter_lotacoes()
                valor_atual = usuario_data['lotacao_permitida']
                index_lotacao = lotacoes.index(valor_atual) if valor_atual in lotacoes else 0
                
                nova_lotacao = st.selectbox(
                    "Lotação Permitida:",
                    lotacoes,
                    index=index_lotacao,
                    key=f"edit_lotacao_{login}"
                )
            
            if st.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                try:
                    self.db.execute(
                        """
                        UPDATE usuarios 
                        SET nome = ?, nivel_acesso = ?, lotacao_permitida = ?
                        WHERE login = ?
                        """,
                        (novo_nome.strip(), novo_nivel, nova_lotacao, login)
                    )
                    
                    audit = AuditLog(self.db)
                    audit.registrar(
                        st.session_state.usuario_nome,
                        "ADMIN",
                        "Editou usuário",
                        f"Alterou dados de {login}"
                    )
                    
                    st.success(f"✅ Dados do usuário {login} atualizados com sucesso!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Erro ao atualizar: {str(e)}")
    
    def _render_resetar_senha(self, login, nome):
        """Resetar senha do usuário"""
        with st.form(f"form_reset_senha_{login}"):
            st.markdown("### 🔑 Resetar Senha do Usuário")
            st.warning(f"Você está prestes a resetar a senha de **{nome}**")
            
            nova_senha = st.text_input(
                "Nova Senha:",
                type="password",
                placeholder="Digite a nova senha (mínimo 6 caracteres)",
                key=f"nova_senha_{login}"
            )
            
            confirmar_senha = st.text_input(
                "Confirmar Nova Senha:",
                type="password",
                placeholder="Digite a nova senha novamente",
                key=f"confirm_senha_{login}"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                reset = st.form_submit_button("🔑 Resetar Senha", type="primary", use_container_width=True)
            
            with col2:
                st.form_submit_button("❌ Cancelar", use_container_width=True)
            
            if reset:
                self._processar_reset_senha(login, nome, nova_senha, confirmar_senha)
    
    def _processar_reset_senha(self, login, nome, nova_senha, confirmar_senha):
        """Processa reset de senha"""
        if not nova_senha:
            st.error("❌ A nova senha é obrigatória!")
            return
        
        if nova_senha != confirmar_senha:
            st.error("❌ As senhas não conferem!")
            return
        
        if len(nova_senha) < 6:
            st.error("❌ A senha deve ter pelo menos 6 caracteres!")
            return
        
        try:
            senha_hash = Security.sha256_hex(nova_senha)
            self.db.execute(
                "UPDATE usuarios SET senha = ? WHERE login = ?",
                (senha_hash, login)
            )
            
            audit = AuditLog(self.db)
            audit.registrar(
                st.session_state.usuario_nome,
                "ADMIN",
                "Resetou senha",
                f"Resetou senha de {login}"
            )
            
            st.success(f"✅ Senha do usuário {nome} resetada com sucesso!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro ao resetar senha: {str(e)}")
    
    def _render_alterar_status(self, login, usuario_data):
        """Ativar/Desativar/Excluir usuário"""
        st.markdown("### 🔄 Alterar Status do Usuário")
        
        status_atual = "ATIVO" if usuario_data['ativo'] == 1 else "INATIVO"
        st.info(f"Status atual: **{status_atual}**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if usuario_data['ativo'] == 1:
                if st.button("🔴 Desativar Usuário", type="secondary", use_container_width=True, key=f"desativar_{login}"):
                    self._processar_desativar_usuario(login)
            else:
                if st.button("🟢 Ativar Usuário", type="primary", use_container_width=True, key=f"ativar_{login}"):
                    self._processar_ativar_usuario(login)
        
        with col2:
            if st.button("🗑️ Excluir Usuário", type="secondary", use_container_width=True, key=f"excluir_{login}"):
                st.session_state.usuario_excluir = {
                    'login': login,
                    'nome': usuario_data['nome']
                }
                st.rerun()
        
        if 'usuario_excluir' in st.session_state and st.session_state.usuario_excluir['login'] == login:
            self._render_modal_exclusao_usuario()
    
    def _processar_desativar_usuario(self, login):
        """Processa desativação de usuário"""
        try:
            if login == st.session_state.usuario_login:
                st.error("❌ Você não pode desativar seu próprio usuário!")
                return
            
            self.db.execute(
                "UPDATE usuarios SET ativo = 0 WHERE login = ?",
                (login,)
            )
            
            audit = AuditLog(self.db)
            audit.registrar(
                st.session_state.usuario_nome,
                "ADMIN",
                "Desativou usuário",
                f"Desativou {login}"
            )
            
            st.success(f"✅ Usuário {login} desativado com sucesso!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro ao desativar: {str(e)}")
    
    def _processar_ativar_usuario(self, login):
        """Processa ativação de usuário"""
        try:
            self.db.execute(
                "UPDATE usuarios SET ativo = 1 WHERE login = ?",
                (login,)
            )
            
            audit = AuditLog(self.db)
            audit.registrar(
                st.session_state.usuario_nome,
                "ADMIN",
                "Ativou usuário",
                f"Ativou {login}"
            )
            
            st.success(f"✅ Usuário {login} ativado com sucesso!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro ao ativar: {str(e)}")
    
    def _render_modal_exclusao_usuario(self):
        """Renderiza modal de confirmação de exclusão de usuário"""
        usuario = st.session_state.usuario_excluir
        
        st.markdown("---")
        st.error("⚠️ **CONFIRMAÇÃO DE EXCLUSÃO DE USUÁRIO**")
        
        st.markdown(f"""
        **Você está prestes a excluir permanentemente este usuário:**
        
        - **Login:** {usuario['login']}
        - **Nome:** {usuario['nome']}
        
        **IMPORTANTE:**
        - O usuário será removido permanentemente do sistema
        - Registros de vacinação feitos por este usuário serão mantidos, mas o campo `usuario_registro` ficará vazio
        - Logs de auditoria serão mantidos para rastreabilidade
        - Esta ação é **IRREVERSÍVEL**
        """)
        
        registros = self.db.fetchone(
            "SELECT COUNT(*) as total FROM doses WHERE usuario_registro = ?",
            (usuario['login'],)
        )
        total_registros = registros['total'] if registros else 0
        
        if total_registros > 0:
            st.warning(f"⚠️ Este usuário possui **{total_registros}** registros de vacinação. Eles serão mantidos no sistema, mas o campo 'usuario_registro' será esvaziado.")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("✅ Confirmar Exclusão", type="primary", use_container_width=True):
                self._processar_exclusao_usuario(usuario, total_registros)
        
        with col2:
            if st.button("❌ Cancelar", use_container_width=True):
                del st.session_state.usuario_excluir
                st.rerun()
    
    def _processar_exclusao_usuario(self, usuario, total_registros):
        """Processa exclusão de usuário"""
        try:
            with self.db.connect() as conn:
                conn.execute(
                    "UPDATE doses SET usuario_registro = NULL WHERE usuario_registro = ?",
                    (usuario['login'],)
                )
                conn.execute(
                    "DELETE FROM usuarios WHERE login = ?",
                    (usuario['login'],)
                )
            
            audit = AuditLog(self.db)
            audit.registrar(
                st.session_state.usuario_nome,
                "ADMIN",
                "Excluiu usuário",
                f"Excluiu {usuario['login']} - {total_registros} registros desassociados"
            )
            
            st.success(f"✅ Usuário {usuario['login']} excluído com sucesso!")
            del st.session_state.usuario_excluir
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro ao excluir: {str(e)}")
    
    def _render_vacinas(self):
        """Renderiza administração de vacinas"""
        st.subheader("💉 Gerenciamento de Vacinas Cadastradas")

        vacinas = self.db.read_sql(
            "SELECT id, nome, fabricante, doses_necessarias, intervalo_dias, via_aplicacao, contraindicacoes, ativo FROM vacinas_cadastradas ORDER BY nome"
        )

        if not vacinas.empty:
            st.success(f"✅ {len(vacinas)} vacinas cadastradas")

            st.dataframe(
                vacinas,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": "ID",
                    "nome": "Nome",
                    "fabricante": "Fabricante",
                    "doses_necessarias": "Doses Necessárias",
                    "intervalo_dias": "Intervalo (dias)",
                    "via_aplicacao": "Via",
                    "contraindicacoes": "Contraindicações",
                    "ativo": "Ativa"
                }
            )

        st.subheader("➕ Nova Vacina")

        with st.form("form_nova_vacina"):
            col1, col2 = st.columns(2)

            with col1:
                nome = st.text_input("Nome da Vacina:*", key="nova_vacina_nome")
                fabricante = st.text_input("Fabricante:", key="nova_vacina_fabricante")
                doses_necessarias = st.number_input(
                    "Doses Necessárias:",
                    min_value=1,
                    max_value=10,
                    value=1,
                    key="nova_vacina_doses"
                )

            with col2:
                intervalo_dias = st.number_input(
                    "Intervalo entre Doses (dias):",
                    min_value=0,
                    max_value=365,
                    value=30,
                    key="nova_vacina_intervalo"
                )

                via_aplicacao = st.selectbox(
                    "Via de Aplicação:",
                    ["Intramuscular", "Subcutânea", "Oral", "Intradérmica"],
                    key="nova_vacina_via"
                )

                contraindicacoes = st.text_area(
                    "Contraindicações:",
                    placeholder="Ex: Gestantes, imunossuprimidos...",
                    height=100,
                    key="nova_vacina_contra"
                )

            ativo = st.checkbox("Ativa", value=True, key="nova_vacina_ativo")

            if st.form_submit_button("💾 Cadastrar Vacina", use_container_width=True):
                self._processar_cadastro_vacina(nome, fabricante, doses_necessarias, 
                                                intervalo_dias, via_aplicacao, contraindicacoes, ativo)
    
    def _processar_cadastro_vacina(self, nome, fabricante, doses, intervalo, via, contra, ativo):
        """Processa cadastro de nova vacina"""
        if not nome.strip():
            st.error("❌ Nome da vacina é obrigatório!")
            return

        try:
            self.db.execute(
                """
                INSERT INTO vacinas_cadastradas
                (nome, fabricante, doses_necessarias, intervalo_dias, via_aplicacao, contraindicacoes, ativo)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (nome.strip(), fabricante.strip() if fabricante else None,
                 doses, intervalo, via,
                 contra.strip() if contra else None,
                 1 if ativo else 0)
            )

            audit = AuditLog(self.db)
            audit.registrar(
                st.session_state.usuario_nome,
                "ADMIN",
                "Cadastrou vacina",
                nome.strip()
            )

            st.success("✅ Vacina cadastrada com sucesso!")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Erro ao cadastrar vacina: {str(e)}")
    
    def _render_utilitarios(self):
        """Renderiza utilitários administrativos"""
        st.subheader("🛠️ Utilitários do Sistema")

        col1, col2 = st.columns(2)

        with col1:
            with st.container():
                st.markdown("### 🔄 Backup Manual do Banco de Dados")
                st.markdown("""
                Crie um backup completo do banco de dados.
                O backup será salvo na pasta local.
                """)

                if st.button("Criar Backup Agora", key="btn_backup", use_container_width=True):
                    self._criar_backup_manual()

        with col2:
            with st.container():
                st.markdown("### 🧹 Limpeza de Dados")
                st.markdown("""
                Remova dados antigos do sistema:
                - Logs antigos
                - Tentativas de login antigas
                """)

                dias_logs = st.number_input(
                    "Manter logs dos últimos (dias):",
                    min_value=7,
                    max_value=365,
                    value=90,
                    key="dias_manter_logs"
                )

                if st.button("Executar Limpeza", key="btn_limpeza", type="secondary", use_container_width=True):
                    self._executar_limpeza(dias_logs)

        st.subheader("🔍 Consulta SQL (Apenas SELECT)")

        sql_query = st.text_area(
            "Digite sua consulta SQL:",
            placeholder="SELECT * FROM servidores LIMIT 10",
            height=100,
            key="sql_query"
        )

        if st.button("Executar Consulta", key="btn_exec_sql", use_container_width=True):
            self._executar_consulta_sql(sql_query)
    
    def _criar_backup_manual(self):
        """Cria backup manual"""
        try:
            backup_path = f"backup_nasst_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

            with open(CONFIG.db_path_v7, 'rb') as src:
                with open(backup_path, 'wb') as dst:
                    dst.write(src.read())

            st.success(f"✅ Backup criado: {backup_path}")

            with open(backup_path, 'rb') as f:
                st.download_button(
                    "📥 Baixar Backup",
                    f.read(),
                    backup_path,
                    "application/x-sqlite3",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"❌ Erro ao criar backup: {str(e)}")
    
    def _executar_limpeza(self, dias_logs):
        """Executa limpeza de dados antigos"""
        with st.spinner("Executando limpeza..."):
            try:
                # Limpar logs
                logs_removidos = self.db.execute(
                    "DELETE FROM logs WHERE data_hora < datetime('now', '-' || ? || ' days')",
                    (str(dias_logs),)
                )

                # Limpar tentativas de login antigas
                tentativas_removidas = self.db.execute(
                    "DELETE FROM login_attempts WHERE data_hora < datetime('now', '-7 days')"
                )

                st.success(f"✅ Limpeza concluída: {logs_removidos} logs removidos, {tentativas_removidas} tentativas antigas removidas")

            except Exception as e:
                st.error(f"❌ Erro na limpeza: {str(e)}")
    
    def _executar_consulta_sql(self, sql_query):
        """Executa consulta SQL personalizada"""
        seguro, mensagem = Security.safe_select_only(sql_query)

        if not seguro:
            st.error(f"❌ {mensagem}")
        else:
            try:
                resultado = self.db.read_sql(sql_query)

                if not resultado.empty:
                    st.success(f"✅ Consulta executada: {len(resultado)} registros")
                    st.dataframe(resultado, use_container_width=True, hide_index=True)

                    csv = resultado.to_csv(index=False)
                    st.download_button(
                        "📥 Exportar CSV",
                        csv,
                        "consulta.csv",
                        "text/csv",
                        use_container_width=True
                    )
                else:
                    st.info("📭 Nenhum resultado encontrado.")

            except Exception as e:
                st.error(f"❌ Erro na consulta: {str(e)}")
    
    def _render_sistema(self):
        """Renderiza informações do sistema"""
        st.subheader("📊 Informações do Sistema")

        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

        with col_stat1:
            total_servidores = self.db.fetchone("SELECT COUNT(*) as c FROM servidores")['c']
            st.metric("Total Servidores", f"{total_servidores:,}")

        with col_stat2:
            total_doses = self.db.fetchone("SELECT COUNT(*) as c FROM doses")['c']
            st.metric("Total Doses", f"{total_doses:,}")

        with col_stat3:
            total_usuarios = self.db.fetchone("SELECT COUNT(*) as c FROM usuarios WHERE ativo = 1")['c']
            st.metric("Usuários Ativos", total_usuarios)

        with col_stat4:
            total_campanhas = self.db.fetchone("SELECT COUNT(*) as c FROM campanhas")['c']
            st.metric("Campanhas", total_campanhas)

        try:
            db_size = os.path.getsize(CONFIG.db_path_v7)
            db_size_mb = db_size / (1024 * 1024)
            st.info(f"**Tamanho do Banco de Dados:** {db_size_mb:.2f} MB")
        except:
            pass

        st.markdown("### 📦 Informações da Versão")

        info_cols = st.columns(2)

        with info_cols[0]:
            st.markdown(f"""
            **Versão do Sistema:** 1.2
            **Ano de Referência:** {CONFIG.ano_atual}
            **Banco de Dados:** SQLite (otimizado)
            **Framework:** Streamlit
            **Desenvolvido em:** Python 3.10+
            """)

        with info_cols[1]:
            st.markdown(f"""
            **Desenvolvedor:** NASST Digital
            **Última Atualização:** {datetime.now().strftime('%d/%m/%Y')}
            **Status:** 🟢 Online
            **Usuário Atual:** {st.session_state.usuario_nome}
            **Nível de Acesso:** {st.session_state.nivel_acesso}
            """)

        if hasattr(self.db, 'get_cache_stats'):
            try:
                cache_stats = self.db.get_cache_stats()
                st.markdown("### ⚡ Estatísticas de Cache")
                col_cache1, col_cache2, col_cache3 = st.columns(3)
                with col_cache1:
                    st.metric("Cache Size", cache_stats['cache_size'])
                with col_cache2:
                    st.metric("Cache Hits", cache_stats['cache_hits'])
                with col_cache3:
                    hit_rate = cache_stats['hit_rate'] * 100
                    st.metric("Hit Rate", f"{hit_rate:.1f}%")
            except:
                pass

    def _render_backup(self):
        """Renderiza configurações de backup automático"""
        st.subheader("💾 Backup Automático do Banco de Dados")
        
        backup_manager = BackupManager(CONFIG.db_path_v7, "backups")
        scheduler = BackupScheduler(backup_manager)
        schedule_config = scheduler.load_schedule()
        
        st.markdown("""
        ### Sobre o Backup Automático
        
        O sistema pode realizar backups automáticos do banco de dados em intervalos regulares.
        Os backups são armazenados na pasta `backups` e podem ser restaurados quando necessário.
        
        **Vantagens:**
        - ✅ Proteção contra perda de dados
        - ✅ Histórico de versões do banco
        - ✅ Restauração rápida em caso de problemas
        - ✅ Backups otimizados usando API nativa do SQLite
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ⚙️ Configurações")
            
            enabled = st.toggle(
                "Ativar backup automático",
                value=schedule_config.get("enabled", False),
                help="Quando ativado, o sistema fará backups automaticamente no intervalo configurado"
            )
            
            interval = st.slider(
                "Intervalo entre backups (horas):",
                min_value=1,
                max_value=168,
                value=schedule_config.get("interval", 6),  # Default 6h para produção
                step=1,
                help="Frequência com que os backups serão realizados"
            )
            
            col_save1, col_save2 = st.columns(2)
            with col_save1:
                if st.button("💾 Salvar Configurações", use_container_width=True):
                    self._salvar_config_backup(scheduler, interval, enabled, backup_manager)
            
            with col_save2:
                if st.button("🔄 Fazer Backup Agora", use_container_width=True, type="primary"):
                    self._fazer_backup_agora(backup_manager)
        
        with col2:
            self._render_lista_backups(backup_manager)
        
        self._render_estatisticas_backup(backup_manager)
    
    def _salvar_config_backup(self, scheduler, interval, enabled, backup_manager):
        """Salva configurações de backup"""
        scheduler.save_schedule(interval, enabled)
        
        if enabled:
            backup_manager.start_auto_backup(
                interval_hours=interval,
                callback=lambda x: st.toast(f"✅ Backup automático concluído: {os.path.basename(x)}")
            )
            st.success(f"✅ Backup automático ativado! Intervalo: {interval} horas")
        else:
            backup_manager.stop_auto_backup()
            st.info("⏹️ Backup automático desativado")
        
        st.rerun()
    
    def _fazer_backup_agora(self, backup_manager):
        """Faz backup manual agora"""
        with st.spinner("Criando backup..."):
            backup_path = backup_manager.create_backup("manual")
            if backup_path:
                st.success(f"✅ Backup criado: {os.path.basename(backup_path)}")
                
                with open(backup_path, 'rb') as f:
                    st.download_button(
                        "📥 Baixar Backup",
                        f.read(),
                        os.path.basename(backup_path),
                        "application/x-sqlite3",
                        use_container_width=True
                    )
            else:
                st.error("❌ Erro ao criar backup")
    
    def _render_lista_backups(self, backup_manager):
        """Renderiza lista de backups disponíveis"""
        st.markdown("### 📋 Backups Disponíveis")
        
        backups = backup_manager.list_backups()
        
        if backups:
            st.info(f"Total de {len(backups)} backups encontrados")
            
            for backup in backups[:10]:
                with st.container():
                    col_b1, col_b2, col_b3 = st.columns([3, 1, 1])
                    
                    with col_b1:
                        st.markdown(f"**{backup['filename']}**")
                        st.caption(f"Criado: {backup['created'].strftime('%d/%m/%Y %H:%M:%S')} | Tamanho: {backup['size_mb']:.2f} MB")
                    
                    with col_b2:
                        if st.button("📥 Baixar", key=f"dl_{backup['filename']}"):
                            with open(backup['path'], 'rb') as f:
                                st.download_button(
                                    "Download",
                                    f.read(),
                                    backup['filename'],
                                    "application/x-sqlite3",
                                    key=f"download_{backup['filename']}"
                                )
                    
                    with col_b3:
                        if st.button("🔄 Restaurar", key=f"restore_{backup['filename']}"):
                            self._confirmar_restauracao(backup)
                    
                    st.markdown("---")
        else:
            st.info("📭 Nenhum backup encontrado. Clique em 'Fazer Backup Agora' para criar o primeiro.")
    
    def _confirmar_restauracao(self, backup):
        """Confirma restauração de backup"""
        st.warning(f"⚠️ Tem certeza que deseja restaurar o backup {backup['filename']}?")
        st.caption("O banco de dados atual será substituído!")
        
        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            if st.button("✅ Sim, restaurar", key=f"confirm_{backup['filename']}"):
                with st.spinner("Restaurando backup..."):
                    backup_manager = BackupManager(CONFIG.db_path_v7, "backups")
                    if backup_manager.restore_backup(backup['path']):
                        st.success("✅ Backup restaurado com sucesso!")
                        st.info("Reinicie a aplicação para aplicar as mudanças.")
                    else:
                        st.error("❌ Erro ao restaurar backup")
        
        with col_confirm2:
            if st.button("❌ Cancelar", key=f"cancel_{backup['filename']}"):
                st.rerun()
    
    def _render_estatisticas_backup(self, backup_manager):
        """Renderiza estatísticas de backup"""
        backups = backup_manager.list_backups()
        
        st.markdown("---")
        st.subheader("📊 Estatísticas de Backup")
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        with col_stat1:
            st.metric("Total de Backups", len(backups))
        
        with col_stat2:
            if backups:
                tamanho_total = sum(b['size'] for b in backups) / (1024 * 1024)
                st.metric("Espaço Total", f"{tamanho_total:.2f} MB")
            else:
                st.metric("Espaço Total", "0 MB")
        
        with col_stat3:
            if backups:
                ultimo = max(backups, key=lambda x: x['created'])
                st.metric("Último Backup", ultimo['created'].strftime('%d/%m/%Y'))
            else:
                st.metric("Último Backup", "Nunca")
        
        with col_stat4:
            if backups:
                primeiro = min(backups, key=lambda x: x['created'])
                st.metric("Primeiro Backup", primeiro['created'].strftime('%d/%m/%Y'))
            else:
                st.metric("Primeiro Backup", "N/A")
        
        with st.expander("📝 Logs de Backup"):
            log_file = os.path.join("backups", "backup.log")
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    logs = f.readlines()[-50:]
                    for log in logs:
                        st.text(log.strip())
            else:
                st.info("Nenhum log encontrado.")
    
    def _render_monitoramento(self):
        """Renderiza monitoramento em tempo real do sistema"""
        st.subheader("📈 Monitoramento em Tempo Real")
        
        # Escolher modo de atualização
        modo = st.radio(
            "Modo de atualização:",
            ["Estático", "Automático (a cada 10s)"],
            horizontal=True,
            key="modo_monitoramento"
        )
        
        if modo == "Automático (a cada 10s)":
            placeholder = st.empty()
            while True:
                with placeholder.container():
                    self._render_metricas_monitoramento()
                    time.sleep(10)
        else:
            self._render_metricas_monitoramento()
    
    def _render_metricas_monitoramento(self):
        """Renderiza as métricas de monitoramento"""
        
        # Métricas em tempo real
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Usuários ativos (baseado em logs recentes)
            usuarios_ativos = self.db.fetchone(
                "SELECT COUNT(DISTINCT usuario) as total FROM logs WHERE data_hora > datetime('now', '-5 minutes')"
            )['total']
            st.metric("👥 Usuários Ativos (5min)", usuarios_ativos)
        
        with col2:
            # Operações por minuto
            ops_ultimo_minuto = self.db.fetchone(
                "SELECT COUNT(*) as total FROM logs WHERE data_hora > datetime('now', '-1 minute')"
            )['total']
            st.metric("⚡ Operações/min", ops_ultimo_minuto)
        
        with col3:
            # Tamanho do banco
            db_size = os.path.getsize(CONFIG.db_path_v7) / (1024 * 1024)
            st.metric("💾 Banco de Dados", f"{db_size:.1f} MB")
        
        with col4:
            # Cache hit rate
            if hasattr(self.db, 'get_cache_stats'):
                stats = self.db.get_cache_stats()
                st.metric("🎯 Cache Hit Rate", f"{stats['hit_rate']*100:.1f}%")
            else:
                st.metric("🎯 Cache Hit Rate", "N/A")
        
        # Gráfico de atividade recente
        st.subheader("📊 Atividade por Hora (últimas 24h)")
        
        atividade = self.db.read_sql("""
            SELECT 
                strftime('%H', data_hora) as hora,
                COUNT(*) as total
            FROM logs
            WHERE data_hora > datetime('now', '-24 hours')
            GROUP BY hora
            ORDER BY hora
        """)
        
        if not atividade.empty:
            import plotly.express as px
            fig = px.bar(
                atividade,
                x='hora',
                y='total',
                title='Distribuição de Atividade por Hora',
                labels={'hora': 'Hora do Dia', 'total': 'Número de Operações'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Logs recentes
        st.subheader("📝 Atividade Recente")
        logs_recentes = self.db.read_sql("""
            SELECT 
                substr(data_hora, 12, 8) as hora,
                usuario,
                modulo,
                acao
            FROM logs 
            ORDER BY data_hora DESC 
            LIMIT 20
        """)
        
        if not logs_recentes.empty:
            st.dataframe(
                logs_recentes,
                use_container_width=True,
                hide_index=True
            )
        
        # Consultas lentas
        st.subheader("⏱️ Consultas Lentas (últimas 24h)")
        log_file = os.path.join("logs", f"nasst_{datetime.now().strftime('%Y%m')}.log")
        
        if os.path.exists(log_file):
            consultas_lentas = []
            with open(log_file, 'r') as f:
                for line in f.readlines()[-1000:]:
                    if "Query lenta" in line:
                        consultas_lentas.append(line.strip())
            
            if consultas_lentas:
                for linha in consultas_lentas[-10:]:
                    st.code(linha, language="text")
            else:
                st.info("Nenhuma consulta lenta registrada nas últimas 24h.")
        else:
            st.info("Arquivo de log não encontrado.")