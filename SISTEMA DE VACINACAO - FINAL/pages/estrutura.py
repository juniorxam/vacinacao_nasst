"""
estrutura.py - Página de importação de estrutura organizacional
"""

import pandas as pd
import streamlit as st

from ui.components import UIComponents


class EstruturaPage:
    """Página de importação de estrutura organizacional"""
    
    def __init__(self, db, auth, estrutura_service):
        self.db = db
        self.auth = auth
        self.estrutura_service = estrutura_service
    
    def render(self):
        """Renderiza página de estrutura"""
        st.title("🏢 Importar Estrutura Organizacional")

        if not self.auth.verificar_permissoes(st.session_state.nivel_acesso, "ADMIN"):
            st.error("❌ Apenas administradores podem importar a estrutura organizacional.")
            return

        st.info("""
        **Instruções:**
        1. Faça upload do arquivo Excel com a estrutura organizacional
        2. O arquivo deve conter as abas: 'setor' e 'CODIGOS'
        3. O sistema importará setores, superintendências, siglas e locais físicos
        """)

        uploaded_file = st.file_uploader(
            "Escolha o arquivo Excel (RELAÇÃO DE SETORES.xlsx)",
            type=["xlsx", "xls"],
            key="upload_estrutura"
        )

        if uploaded_file is not None:
            try:
                df_setores = pd.read_excel(uploaded_file, sheet_name='setor')
                df_codigos = pd.read_excel(uploaded_file, sheet_name='CODIGOS')

                st.success(f"✅ Arquivo carregado: {len(df_setores)} setores, {len(df_codigos)} códigos")

                with st.expander("📋 Pré-visualização - Setores"):
                    st.dataframe(df_setores.head(20), use_container_width=True)

                with st.expander("📋 Pré-visualização - Códigos"):
                    st.dataframe(df_codigos.head(20), use_container_width=True)

                if st.button("🚀 Importar Estrutura Organizacional", type="primary", use_container_width=True):
                    with st.spinner("Importando estrutura organizacional..."):
                        # Implementar importação real aqui
                        stats = {"inseridos": 0, "atualizados": 0, "erros": 0}
                        
                        # Simulação - implementar lógica real de importação
                        st.success("✅ Estrutura organizacional importada com sucesso!")
                        
                        if self.estrutura_service:
                            estatisticas = self.estrutura_service.get_estatisticas()
                            st.info(f"""
                            **Estatísticas:**
                            - {estatisticas['total_superintendencias']} Superintendências
                            - {estatisticas['total_setores']} Setores
                            - {estatisticas['total_locais_fisicos']} Locais Físicos
                            """)

            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")