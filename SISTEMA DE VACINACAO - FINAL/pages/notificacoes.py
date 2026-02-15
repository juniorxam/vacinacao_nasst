"""
notificacoes.py - Página de notificações via WhatsApp
"""

from datetime import date, timedelta
import pandas as pd
import streamlit as st

from core.whatsapp_service import NotificacaoCampanhaService, WhatsAppService
from core.security import Formatters
from ui.components import UIComponents


class NotificacoesPage:
    """Página de notificações via WhatsApp"""
    
    def __init__(self, db, auth, audit):
        self.db = db
        self.auth = auth
        self.audit = audit
        self.notificacao_service = NotificacaoCampanhaService(db)
    
    def render(self):
        """Renderiza página de notificações"""
        st.title("📱 Notificações via WhatsApp")
        UIComponents.breadcrumb("🏠 Início", "Notificações")

        # Verificar permissão
        if not self.auth.verificar_permissoes(st.session_state.nivel_acesso, "OPERADOR"):
            st.error("❌ Apenas operadores e administradores podem acessar esta página.")
            return

        # Abas
        tab1, tab2, tab3 = st.tabs([
            "📢 Campanhas", 
            "📅 Lembretes de Dose",
            "📤 Envio em Massa"
        ])

        with tab1:
            self._render_campanhas()
        
        with tab2:
            self._render_lembretes()
        
        with tab3:
            self._render_envio_massa()
    
    def _render_campanhas(self):
        """Renderiza notificações de campanhas"""
        st.subheader("📢 Notificar sobre Campanhas")
        
        # Buscar campanhas ativas
        campanhas = self.db.read_sql("""
            SELECT id, nome_campanha, vacina, data_inicio, data_fim, status, publico_alvo
            FROM campanhas
            WHERE status = 'ATIVA'
            ORDER BY data_inicio DESC
        """)
        
        if campanhas.empty:
            st.info("Não há campanhas ativas no momento.")
            return
        
        # Selecionar campanha
        opcoes_campanha = {
            f"{row['nome_campanha']} ({Formatters.formatar_data_br(row['data_inicio'])} a {Formatters.formatar_data_br(row['data_fim'])})": row['id']
            for _, row in campanhas.iterrows()
        }
        
        campanha_selecionada = st.selectbox(
            "Selecione a campanha:",
            list(opcoes_campanha.keys()),
            key="select_campanha_notif"
        )
        
        if campanha_selecionada:
            campanha_id = opcoes_campanha[campanha_selecionada]
            
            # Buscar dados da campanha
            campanha = self.db.fetchone(
                "SELECT * FROM campanhas WHERE id = ?",
                (campanha_id,)
            )
            
            # Buscar servidores elegíveis
            with st.spinner("Buscando servidores elegíveis..."):
                servidores = self.notificacao_service.buscar_servidores_para_campanha(campanha_id)
            
            if servidores.empty:
                st.warning("Nenhum servidor com telefone cadastrado encontrado para esta campanha.")
                return
            
            st.success(f"✅ {len(servidores)} servidores elegíveis com telefone cadastrado.")
            
            # Pré-visualização
            with st.expander("📋 Servidores elegíveis (amostra)"):
                st.dataframe(servidores[['nome', 'lotacao', 'telefone']].head(10), use_container_width=True)
                if len(servidores) > 10:
                    st.caption(f"... e mais {len(servidores) - 10} servidores")
            
            # Personalizar mensagem
            st.markdown("### ✏️ Personalizar Mensagem")
            
            mensagem_personalizada = st.text_area(
                "Mensagem (você pode personalizar):",
                value=self.notificacao_service.gerar_mensagem_campanha(
                    {'nome': 'SERVIDOR'}, 
                    dict(campanha)
                ).replace('SERVIDOR', '{nome}'),
                height=200,
                help="Use {nome} para inserir o nome do servidor"
            )
            
            # Opções de envio
            col1, col2 = st.columns(2)
            
            with col1:
                limite_envio = st.number_input(
                    "Limite de envios (0 para todos):",
                    min_value=0,
                    max_value=100,
                    value=10
                )
            
            # Botões de ação
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button("🔗 Gerar Links", use_container_width=True):
                    self._gerar_links_campanha(servidores, campanha, mensagem_personalizada, limite_envio)
            
            with col_btn2:
                if st.button("📋 Copiar Lista", use_container_width=True):
                    self._gerar_lista_telefones(servidores)
            
            with col_btn3:
                if st.button("📤 Enviar Lote (Abrir Múltiplos)", use_container_width=True):
                    self._abrir_multiplos_whatsapp(servidores, campanha, mensagem_personalizada, limite_envio)
    
    def _render_lembretes(self):
        """Renderiza lembretes de doses agendadas"""
        st.subheader("📅 Lembretes de Doses Agendadas")
        
        dias = st.slider("Dias de antecedência:", 1, 30, 7)
        
        with st.spinner("Buscando doses agendadas..."):
            servidores = self.notificacao_service.buscar_servidores_com_doses_agendadas(dias)
        
        if servidores.empty:
            st.info(f"Nenhuma dose agendada para os próximos {dias} dias.")
            return
        
        st.success(f"✅ {len(servidores)} doses agendadas nos próximos {dias} dias.")
        
        # Pré-visualização
        st.dataframe(
            servidores[['nome', 'vacina', 'dose', 'data_agendamento', 'telefone']], 
            use_container_width=True
        )
        
        # Opções de envio
        col1, col2 = st.columns(2)
        
        with col1:
            limite_envio = st.number_input(
                "Limite de envios:",
                min_value=1,
                max_value=len(servidores),
                value=min(10, len(servidores)),
                key="limite_lembrete"
            )
        
        with col2:
            if st.button("🔗 Gerar Links de Lembrete", use_container_width=True):
                self._gerar_links_lembretes(servidores, limite_envio)
    
    def _render_envio_massa(self):
        """Renderiza envio em massa personalizado"""
        st.subheader("📤 Envio em Massa Personalizado")
        
        st.info("""
        Selecione um grupo de servidores e envie uma mensagem personalizada.
        """)
        
        # Filtros
        col1, col2 = st.columns(2)
        
        with col1:
            superintendencia = st.selectbox(
                "Superintendência:",
                ["TODAS"] + self._get_superintendencias(),
                key="filtro_super_massa"
            )
        
        with col2:
            lotacao = st.selectbox(
                "Lotação:",
                ["TODAS"] + self._get_lotacoes(),
                key="filtro_lotacao_massa"
            )
        
        # Buscar servidores
        if st.button("🔍 Buscar Servidores", use_container_width=True):
            query = """
                SELECT id_comp, nome, telefone, lotacao, superintendencia
                FROM servidores
                WHERE situacao_funcional = 'ATIVO'
                  AND telefone IS NOT NULL 
                  AND telefone != ''
                  AND telefone != 'Nao informado'
            """
            params = []
            
            if superintendencia != "TODAS":
                query += " AND superintendencia = ?"
                params.append(superintendencia)
            
            if lotacao != "TODAS":
                query += " AND lotacao = ?"
                params.append(lotacao)
            
            servidores = self.db.read_sql(query, params)
            st.session_state.servidores_massa_notif = servidores
        
        if 'servidores_massa_notif' in st.session_state:
            servidores = st.session_state.servidores_massa_notif
            
            if not servidores.empty:
                st.success(f"✅ {len(servidores)} servidores encontrados.")
                
                # Pré-visualização
                with st.expander("📋 Servidores encontrados"):
                    st.dataframe(servidores[['nome', 'lotacao', 'telefone']], use_container_width=True)
                
                # Mensagem personalizada
                st.markdown("### ✏️ Mensagem")
                mensagem = st.text_area(
                    "Digite sua mensagem (use {nome} para inserir o nome do servidor):",
                    value="Olá {nome},\n\nEsta é uma mensagem da Secretaria de Saúde.",
                    height=150
                )
                
                # Opções
                limite = st.number_input("Limite de envios:", 1, len(servidores), min(20, len(servidores)))
                
                if st.button("🔗 Gerar Links", use_container_width=True):
                    self._gerar_links_personalizados(servidores, mensagem, limite)
    
    def _gerar_links_campanha(self, servidores, campanha, mensagem_template, limite):
        """Gera links para campanha"""
        resultados = []
        
        servidores_lista = servidores.head(limite) if limite > 0 else servidores
        
        for _, servidor in servidores_lista.iterrows():
            mensagem = mensagem_template.replace('{nome}', servidor['nome'].split()[0])
            link = WhatsAppService.gerar_link_whatsapp(servidor['telefone'], mensagem)
            
            resultados.append({
                'nome': servidor['nome'],
                'telefone': WhatsAppService.formatar_telefone(servidor['telefone']),
                'link': link
            })
        
        self._exibir_resultados(resultados, f"campanha_{campanha['id']}")
    
    def _gerar_links_lembretes(self, servidores, limite):
        """Gera links para lembretes de dose"""
        resultados = []
        
        for _, dose in servidores.head(limite).iterrows():
            mensagem = self.notificacao_service.gerar_mensagem_dose_agendada(
                {'nome': dose['nome']},
                dose
            )
            link = WhatsAppService.gerar_link_whatsapp(dose['telefone'], mensagem)
            
            resultados.append({
                'nome': dose['nome'],
                'vacina': f"{dose['vacina']} - {dose['dose']}",
                'data': Formatters.formatar_data_br(dose['data_agendamento']),
                'telefone': WhatsAppService.formatar_telefone(dose['telefone']),
                'link': link
            })
        
        self._exibir_resultados(resultados, "lembretes")
    
    def _gerar_links_personalizados(self, servidores, mensagem_template, limite):
        """Gera links personalizados"""
        resultados = []
        
        for _, servidor in servidores.head(limite).iterrows():
            mensagem = mensagem_template.replace('{nome}', servidor['nome'].split()[0])
            link = WhatsAppService.gerar_link_whatsapp(servidor['telefone'], mensagem)
            
            resultados.append({
                'nome': servidor['nome'],
                'telefone': WhatsAppService.formatar_telefone(servidor['telefone']),
                'lotacao': servidor['lotacao'],
                'link': link
            })
        
        self._exibir_resultados(resultados, "personalizado")
    
    def _gerar_lista_telefones(self, servidores):
        """Gera uma lista de telefones para cópia"""
        telefones = [WhatsAppService.formatar_telefone(t) for t in servidores['telefone'].tolist()]
        lista = "\n".join(telefones)
        
        st.code(lista, language="text")
        st.info("Copie a lista acima para usar em outros aplicativos.")
    
    def _abrir_multiplos_whatsapp(self, servidores, campanha, mensagem_template, limite):
        """
        Gera links que abrem múltiplas conversas (útil para WhatsApp Web)
        """
        servidores_lista = servidores.head(limite) if limite > 0 else servidores
        
        links = []
        for _, servidor in servidores_lista.iterrows():
            mensagem = mensagem_template.replace('{nome}', servidor['nome'].split()[0])
            link = WhatsAppService.gerar_link_whatsapp(servidor['telefone'], mensagem)
            links.append(link)
        
        # Mostrar links em uma tabela
        st.markdown("### 🔗 Links gerados (clique para abrir)")
        
        df_links = pd.DataFrame({
            'Servidor': servidores_lista['nome'].tolist(),
            'Telefone': [WhatsAppService.formatar_telefone(t) for t in servidores_lista['telefone'].tolist()],
            'Link': links
        })
        
        for _, row in df_links.iterrows():
            st.markdown(f"📱 **{row['Servidor']}** - {row['Telefone']}")
            st.markdown(f"[🔗 Abrir WhatsApp]({row['Link']})")
            st.markdown("---")
    
    def _exibir_resultados(self, resultados, key_suffix):
        """Exibe os resultados em uma tabela"""
        if not resultados:
            st.warning("Nenhum resultado gerado.")
            return
        
        df = pd.DataFrame(resultados)
        
        st.markdown("### 🔗 Links gerados")
        st.dataframe(df, use_container_width=True)
        
        # Botão para copiar todos os links
        links_texto = "\n".join([f"{r['nome']}: {r['link']}" for r in resultados])
        st.download_button(
            "📋 Copiar Links",
            links_texto,
            f"links_{key_suffix}.txt",
            "text/plain"
        )
    
    def _get_superintendencias(self):
        """Retorna lista de superintendências"""
        df = self.db.read_sql(
            "SELECT DISTINCT superintendencia FROM servidores WHERE superintendencia IS NOT NULL ORDER BY superintendencia"
        )
        return df['superintendencia'].tolist() if not df.empty else []
    
    def _get_lotacoes(self):
        """Retorna lista de lotações"""
        df = self.db.read_sql(
            "SELECT DISTINCT lotacao FROM servidores WHERE lotacao IS NOT NULL ORDER BY lotacao"
        )
        return df['lotacao'].tolist() if not df.empty else []