"""
importador.py - Componente reutilizável para importação de servidores em lote
"""

import pandas as pd
import streamlit as st
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ImportadorServidores:
    """
    Classe dedicada à importação de servidores em lote
    Separa a lógica de UI da lógica de negócio
    """
    
    def __init__(self, servidores_service, db):
        """
        Args:
            servidores_service: Serviço de servidores (com métodos de importação)
            db: Conexão com banco de dados
        """
        self.service = servidores_service
        self.db = db
        self.MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
        
    def render(self):
        """Renderiza todo o fluxo de importação"""
        
        # Etapa 1: Upload do arquivo
        uploaded_file = self._render_upload()
        if not uploaded_file:
            return
        
        # Etapa 2: Carregar arquivo
        df_raw = self._carregar_arquivo(uploaded_file)
        if df_raw is None:
            return
        
        # Etapa 3: Mapeamento de colunas
        mapeamento = self._render_mapeamento(df_raw)
        if not mapeamento:
            return
        
        # Etapa 4: Opções de importação
        opcoes = self._render_opcoes()
        
        # Etapa 5: Executar importação
        if st.button("🚀 Executar Importação", type="primary", use_container_width=True):
            self._executar_importacao(df_raw, mapeamento, opcoes)
    
    def _render_upload(self):
        """Etapa 1: Upload do arquivo com validação de tamanho"""
        st.subheader("📥 Upload do Arquivo")
        
        st.info("""
        **Instruções para importação:**
        1. Prepare um arquivo Excel ou CSV com os dados dos servidores
        2. O arquivo deve ter no máximo 10MB
        3. Faça o upload do arquivo
        4. Mapeie as colunas do arquivo para os campos do sistema
        5. Configure as opções de importação
        6. Execute a importação
        """)
        
        uploaded_file = st.file_uploader(
            "Escolha um arquivo (CSV, Excel)",
            type=["csv", "xlsx", "xls"],
            key="upload_servidores"
        )
        
        if uploaded_file is not None:
            # Validar tamanho do arquivo
            if uploaded_file.size > self.MAX_FILE_SIZE:
                st.error(f"❌ Arquivo muito grande ({uploaded_file.size/1024/1024:.1f}MB). Máximo permitido: 10MB")
                return None
            
            # Validar extensão (reforço)
            if not uploaded_file.name.lower().endswith(('.csv', '.xlsx', '.xls')):
                st.error("❌ Tipo de arquivo não permitido. Use CSV ou Excel.")
                return None
            
        return uploaded_file
    
    def _carregar_arquivo(self, uploaded_file):
        """Carrega o arquivo em DataFrame"""
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, dtype=str, encoding='utf-8')
            else:
                df = pd.read_excel(uploaded_file, dtype=str)
            
            st.success(f"✅ {len(df)} registros carregados com sucesso!")
            
            with st.expander("📋 Pré-visualização do arquivo (primeiras 10 linhas)"):
                st.dataframe(df.head(10), use_container_width=True)
            
            return df
            
        except Exception as e:
            st.error(f"❌ Erro ao ler arquivo: {str(e)}")
            logger.error(f"Erro ao carregar arquivo: {e}", exc_info=True)
            return None
    
    def _render_mapeamento(self, df):
        """Etapa 2: Mapeamento de colunas com detecção automática"""
        st.subheader("⚙️ Mapeamento de Colunas")
        st.caption("Selecione para cada campo do sistema qual coluna do arquivo corresponde")
        
        # Detectar colunas automaticamente
        colunas_detectadas = self.service.detectar_colunas_arquivo(df)
        
        mapeamento = {}
        
        # Campos obrigatórios
        campos_obrigatorios = ["NOME", "CPF", "NUMFUNC", "NUMVINC", "LOTACAO"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔴 Campos obrigatórios:**")
            for campo in campos_obrigatorios:
                default = colunas_detectadas.get(campo, "")
                options = [""] + list(df.columns)
                
                # Encontrar índice do default
                try:
                    index = options.index(default) if default in options else 0
                except ValueError:
                    index = 0
                
                mapeamento[campo] = st.selectbox(
                    f"{campo}:",
                    options,
                    index=index,
                    key=f"map_{campo}",
                    help=f"Selecione a coluna que contém {campo}"
                )
        
        # Campos opcionais
        campos_opcionais = [
            "SUPERINTENDENCIA", "CARGO", "TELEFONE", "EMAIL", 
            "DATA_NASCIMENTO", "SEXO", "DATA_ADMISSAO", 
            "LOTACAO_FISICA", "TIPO_VINCULO", "SITUACAO_FUNCIONAL"
        ]
        
        with col2:
            st.markdown("**🟢 Campos opcionais:**")
            for campo in campos_opcionais:
                default = colunas_detectadas.get(campo, "")
                options = [""] + list(df.columns)
                
                try:
                    index = options.index(default) if default in options else 0
                except ValueError:
                    index = 0
                
                mapeamento[campo] = st.selectbox(
                    f"{campo}:",
                    options,
                    index=index,
                    key=f"map_opt_{campo}",
                    help=f"Selecione a coluna que contém {campo} (opcional)"
                )
        
        # Validar campos obrigatórios
        campos_nao_mapeados = [campo for campo in campos_obrigatorios if not mapeamento.get(campo)]
        if campos_nao_mapeados:
            st.error(f"❌ Campos obrigatórios não mapeados: {', '.join(campos_nao_mapeados)}")
            return None
        
        # Mostrar resumo do mapeamento
        with st.expander("📊 Resumo do mapeamento"):
            resumo = {}
            for campo, coluna in mapeamento.items():
                if coluna:
                    resumo[campo] = coluna
            st.json(resumo)
        
        return mapeamento
    
    def _render_opcoes(self):
        """Etapa 3: Opções de importação"""
        st.subheader("🔧 Opções de Importação")
        
        col1, col2 = st.columns(2)
        
        with col1:
            acao_duplicados = st.selectbox(
                "Servidores já cadastrados:",
                [
                    "Manter existente e ignorar novo",
                    "Sobrescrever todos os dados",
                    "Atualizar apenas campos vazios"
                ],
                key="acao_duplicados",
                help="O que fazer quando um servidor já existe no banco"
            )
            
            criar_novos = st.checkbox(
                "Criar novos servidores",
                value=True,
                key="criar_novos",
                help="Criar registros para servidores não encontrados"
            )
        
        with col2:
            atualizar_vazios = st.checkbox(
                "Atualizar campos vazios",
                value=True,
                key="atualizar_vazios",
                help="Preencher campos vazios nos registros existentes"
            )
            
            notificar_diferencas = st.checkbox(
                "Notificar diferenças",
                value=True,
                key="notificar_diferencas",
                help="Mostrar alerta quando houver diferenças nos dados"
            )
        
        return {
            'acao_duplicados': acao_duplicados,
            'criar_novos': criar_novos,
            'atualizar_vazios': atualizar_vazios,
            'notificar_diferencas': notificar_diferencas
        }
    
    def _executar_importacao(self, df, mapeamento, opcoes):
        """Etapa 4: Executar importação"""
        with st.spinner("Processando importação... Isso pode levar alguns segundos."):
            try:
                stats, erros, diferencas = self.service.importar_em_lote(
                    df_raw=df,
                    mapeamento_final=mapeamento,
                    acao_duplicados=opcoes['acao_duplicados'],
                    modo_comparacao="CPF",
                    criar_novos=opcoes['criar_novos'],
                    atualizar_vazios=opcoes['atualizar_vazios'],
                    notificar_diferencas=opcoes['notificar_diferencas'],
                    usuario=st.session_state.usuario_nome,
                )
                
                self._exibir_resultados(stats, erros, diferencas)
                
            except Exception as e:
                st.error(f"❌ Erro durante a importação: {str(e)}")
                logger.error(f"Erro na importação: {e}", exc_info=True)
    
    def _exibir_resultados(self, stats, erros, diferencas):
        """Exibe resultados da importação"""
        st.subheader("📊 Resultado da Importação")
        
        # Métricas principais
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("✅ Inseridos", stats["inseridos"])
        with col2:
            st.metric("🔄 Atualizados", stats["atualizados"])
        with col3:
            st.metric("⏭️ Ignorados", stats["ignorados"])
        with col4:
            st.metric("❌ Erros", stats["erros"])
        
        # Diferenças detectadas
        if diferencas:
            st.warning(f"⚠️ {stats.get('diferencas_detectadas', len(diferencas))} diferenças detectadas")
            with st.expander("Ver detalhes das diferenças"):
                for i, diff in enumerate(diferencas[:10]):
                    st.markdown(f"**Registro {i+1}:** {diff.get('nome', 'N/A')}")
                    st.json(diff.get('diferencas', {}))
                
                if len(diferencas) > 10:
                    st.caption(f"... e mais {len(diferencas) - 10} diferenças")
        
        # Erros
        if erros:
            st.error(f"❌ {len(erros)} erros encontrados")
            with st.expander("Ver lista de erros"):
                for erro in erros[:20]:
                    st.error(erro)
                
                if len(erros) > 20:
                    st.caption(f"... e mais {len(erros) - 20} erros")
        
        # Mensagem de sucesso
        if stats["erros"] == 0 and (stats["inseridos"] + stats["atualizados"]) > 0:
            st.success("✅ Importação concluída com sucesso!")
            st.balloons()
        elif stats["erros"] == 0 and stats["inseridos"] == 0 and stats["atualizados"] == 0:
            st.info("📭 Nenhum registro novo ou atualizado. Todos os dados já existiam.")