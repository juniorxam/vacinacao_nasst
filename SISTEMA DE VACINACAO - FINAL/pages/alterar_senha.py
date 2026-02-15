"""
alterar_senha.py - Página para usuário alterar própria senha
"""

import streamlit as st

from config import CONFIG
from core.security import Security
from ui.components import UIComponents


class AlterarSenhaPage:
    """Página para alteração de senha do próprio usuário"""
    
    def __init__(self, db, auth, audit):
        self.db = db
        self.auth = auth
        self.audit = audit
    
    def render(self):
        """Renderiza página de alteração de senha"""
        st.title("🔐 Alterar Minha Senha")
        UIComponents.breadcrumb("🏠 Início", "Alterar Senha")
        
        # Pega o LOGIN e o NOME da sessão
        usuario_login = st.session_state.get('usuario_login', '')
        usuario_nome = st.session_state.get('usuario_nome', 'Usuário')
        nivel_acesso = st.session_state.get('nivel_acesso', 'VISUALIZADOR')
        
        # Se não tiver login na sessão, tenta buscar pelo nome (fallback)
        if not usuario_login and usuario_nome:
            row = self.db.fetchone(
                "SELECT login FROM usuarios WHERE nome = ? AND ativo = 1",
                (usuario_nome,)
            )
            if row:
                usuario_login = row['login']
                st.session_state.usuario_login = usuario_login  # Salva para próximas vezes
        
        if not usuario_login:
            st.error("❌ Erro: Não foi possível identificar o login do usuário!")
            st.stop()
        
        st.info(f"**Usuário:** {usuario_nome} | **Login:** {usuario_login} | **Nível:** {nivel_acesso}")
        st.markdown("---")

        # Cria uma variável de controle para saber se a senha foi alterada
        if 'senha_alterada' not in st.session_state:
            st.session_state.senha_alterada = False

        # Se a senha já foi alterada, mostra apenas a mensagem de sucesso e o botão
        if st.session_state.senha_alterada:
            st.success("✅ Senha alterada com sucesso!")
            st.balloons()
            st.info("🔐 Use sua nova senha no próximo login.")
            
            # Botão para voltar ao dashboard
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🏠 Voltar ao Dashboard", use_container_width=True, type="primary", key="btn_voltar_dashboard"):
                    st.session_state.senha_alterada = False
                    st.session_state.pagina_atual = "dashboard"
                    st.rerun()
            return

        # FORMULÁRIO de alteração de senha
        with st.form("form_alterar_senha"):
            st.markdown("### 🔑 Alterar Senha")
            
            col1, col2 = st.columns(2)
            
            with col1:
                senha_atual = st.text_input(
                    "Senha Atual:",
                    type="password",
                    placeholder="Digite sua senha atual",
                    key="senha_atual"
                )
            
            with col2:
                st.markdown(" ")  # Espaço vazio para alinhamento
            
            nova_senha = st.text_input(
                "Nova Senha:",
                type="password",
                placeholder="Digite a nova senha (mínimo 6 caracteres)",
                key="nova_senha",
                help="A senha deve ter pelo menos 6 caracteres"
            )
            
            confirmar_senha = st.text_input(
                "Confirmar Nova Senha:",
                type="password",
                placeholder="Digite a nova senha novamente",
                key="confirmar_senha"
            )
            
            st.markdown("### 📋 Requisitos da senha:")
            st.markdown("""
            - ✅ Mínimo de 6 caracteres
            - ✅ Não pode ser igual à senha atual
            - ✅ Recomendado usar letras e números
            """)
            
            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
            
            with col_btn1:
                # CORREÇÃO: Substituir width='stretch' por use_container_width=True
                submit = st.form_submit_button(
                    "✅ Alterar Senha",
                    type="primary",
                    use_container_width=True
                )
            
            with col_btn2:
                # CORREÇÃO: Substituir width='stretch' por use_container_width=True
                cancelar = st.form_submit_button(
                    "❌ Cancelar",
                    use_container_width=True
                )
            
            if submit:
                self._processar_alteracao(usuario_login, usuario_nome, senha_atual, nova_senha, confirmar_senha)
            
            if cancelar:
                st.session_state.pagina_atual = "dashboard"
                st.rerun()
    
    def _processar_alteracao(self, usuario_login, usuario_nome, senha_atual, nova_senha, confirmar_senha):
        """Processa a alteração de senha"""
        
        # Validação 1: Login está disponível
        if not usuario_login:
            st.error("❌ Erro: Login do usuário não encontrado!")
            st.stop()
        
        # Validação 2: Senha atual foi informada
        if not senha_atual:
            st.error("❌ A senha atual é obrigatória!")
            st.stop()
        
        # Validação 3: Nova senha foi informada
        if not nova_senha:
            st.error("❌ A nova senha é obrigatória!")
            st.stop()
        
        # Validação 4: Confirmação foi informada
        if not confirmar_senha:
            st.error("❌ A confirmação da senha é obrigatória!")
            st.stop()
        
        # Validação 5: Nova senha e confirmação conferem
        if nova_senha != confirmar_senha:
            st.error("❌ As senhas não conferem!")
            self.audit.registrar(
                usuario_login,
                "AUTH",
                "Tentativa falha de alteração de senha",
                "Confirmação de senha não confere",
                "127.0.0.1"
            )
            st.stop()
        
        # Validação 6: Tamanho mínimo da nova senha
        if len(nova_senha) < 6:
            st.error("❌ A nova senha deve ter pelo menos 6 caracteres!")
            st.stop()
        
        # Verifica senha atual no banco usando o LOGIN
        senha_atual_hash = Security.sha256_hex(senha_atual)
        
        row = self.db.fetchone(
            "SELECT login FROM usuarios WHERE login = ? AND senha = ? AND ativo = 1",
            (usuario_login, senha_atual_hash)
        )
        
        if not row:
            st.error("❌ Senha atual incorreta!")
            self.audit.registrar(
                usuario_login,
                "AUTH",
                "Tentativa falha de alteração de senha",
                "Senha atual incorreta",
                "127.0.0.1"
            )
            st.stop()
        
        # Verifica se a nova senha é igual à atual
        if nova_senha == senha_atual:
            st.error("❌ A nova senha não pode ser igual à senha atual!")
            st.stop()
        
        # Atualiza a senha no banco
        try:
            nova_senha_hash = Security.sha256_hex(nova_senha)
            self.db.execute(
                "UPDATE usuarios SET senha = ? WHERE login = ?",
                (nova_senha_hash, usuario_login)
            )
            
            # Registra no log de auditoria
            self.audit.registrar(
                usuario_login,
                "AUTH",
                "Alterou própria senha",
                "Senha alterada com sucesso",
                "127.0.0.1"
            )
            
            # Marca que a senha foi alterada e rerun para mostrar a tela de sucesso
            st.session_state.senha_alterada = True
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Erro ao alterar senha: {str(e)}")
            self.audit.registrar(
                usuario_login,
                "AUTH",
                "Erro ao alterar senha",
                f"Erro: {str(e)}",
                "127.0.0.1"
            )