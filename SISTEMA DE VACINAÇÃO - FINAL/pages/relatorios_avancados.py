"""
relatorios_avancados.py - Página de relatórios avançados
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import date, datetime
import io
import base64
import tempfile
import os

from config import CONFIG
from ui.components import UIComponents
from core.relatorio_service import RelatorioPDFService

# Importar reportlab para geração de PDF avançado
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.widgets.grids import Grid
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    st.warning("Biblioteca reportlab não instalada. A geração de PDF avançado será limitada.")


class RelatoriosAvancadosPage:
    """Página de relatórios avançados"""
    
    def __init__(self, db, relatorios, auth):
        self.db = db
        self.relatorios = relatorios
        self.auth = auth
    
    def render(self):
        """Renderiza página de relatórios avançados"""
        st.title("📈 Relatórios Avançados")
        UIComponents.breadcrumb("🏠 Início", "Relatórios Avançados")

        if not self.auth.verificar_permissoes(st.session_state.nivel_acesso, "OPERADOR"):
            st.error("❌ Apenas operadores e administradores podem acessar relatórios avançados.")
            return

        # Seletor de período para todos os relatórios
        st.subheader("📅 Período de Análise")
        
        col_per1, col_per2, col_per3 = st.columns(3)
        
        with col_per1:
            data_inicio = st.date_input(
                "Data inicial:",
                value=date(date.today().year, 1, 1),
                key="rel_data_inicio"
            )
        
        with col_per2:
            data_fim = st.date_input(
                "Data final:",
                value=date.today(),
                key="rel_data_fim"
            )
        
        with col_per3:
            incluir_todos = st.checkbox("Incluir todo o histórico", value=False)
            if incluir_todos:
                st.caption("Serão considerados todos os dados disponíveis")
        
        # Botão para gerar PDF completo
        st.markdown("---")
        col_pdf1, col_pdf2, col_pdf3 = st.columns([1, 2, 1])
        with col_pdf2:
            if st.button("📄 GERAR RELATÓRIO COMPLETO EM PDF", type="primary", use_container_width=True):
                self._gerar_pdf_completo(data_inicio, data_fim, incluir_todos)
        
        st.markdown("---")

        # Layout em colunas para os cards de relatórios
        col1, col2 = st.columns(2)

        with col1:
            with st.container():
                st.markdown("### 📅 Tendência Temporal")
                st.markdown("""
                Análise de tendência de vacinação:
                - Evolução mensal
                - Comparativo anual
                - Sazonalidade
                """)
                if st.button("📊 Analisar Tendência", key="rel_tendencia", use_container_width=True):
                    st.session_state.relatorio_avancado = "tendencia"
                    st.rerun()

        with col2:
            with st.container():
                st.markdown("### 👥 Análise Demográfica")
                st.markdown("""
                Perfil demográfico dos vacinados:
                - Faixa etária
                - Distribuição por sexo
                - Superintendência/lotação
                """)
                if st.button("📊 Analisar Demografia", key="rel_demografico", use_container_width=True):
                    st.session_state.relatorio_avancado = "demografico"
                    st.rerun()

        col3, col4 = st.columns(2)

        with col3:
            with st.container():
                st.markdown("### 💉 Eficiência de Vacinas")
                st.markdown("""
                Análise de eficiência:
                - Cobertura por vacina
                - Taxa de retorno
                - Adesão às doses
                """)
                if st.button("📊 Analisar Eficiência", key="rel_eficiencia", use_container_width=True):
                    st.session_state.relatorio_avancado = "eficiencia"
                    st.rerun()

        with col4:
            with st.container():
                st.markdown("### 🎯 Metas e Objetivos")
                st.markdown("""
                Acompanhamento de metas:
                - Progresso de campanhas
                - Metas vs Realizado
                - Gaps de cobertura
                """)
                if st.button("📊 Analisar Metas", key="rel_metas", use_container_width=True):
                    st.session_state.relatorio_avancado = "metas"
                    st.rerun()

        if hasattr(st.session_state, 'relatorio_avancado'):
            st.markdown("---")
            self._render_relatorio(st.session_state.relatorio_avancado, data_inicio, data_fim, incluir_todos)
    
    def _render_relatorio(self, tipo: str, data_inicio, data_fim, incluir_todos):
        """Renderiza relatório avançado específico"""
        if tipo == "tendencia":
            self._render_tendencia(data_inicio, data_fim, incluir_todos)
        elif tipo == "demografico":
            self._render_demografico(data_inicio, data_fim, incluir_todos)
        elif tipo == "eficiencia":
            self._render_eficiencia(data_inicio, data_fim, incluir_todos)
        elif tipo == "metas":
            self._render_metas(data_inicio, data_fim, incluir_todos)
    
    def _render_tendencia(self, data_inicio, data_fim, incluir_todos):
        """Renderiza análise de tendência temporal"""
        st.subheader("📅 Análise de Tendência Temporal")

        # Construir query com filtro de data
        query = """
            SELECT strftime('%Y-%m', data_ap) AS mes,
                   COUNT(*) AS total_doses,
                   vacina
            FROM doses
            WHERE data_ap IS NOT NULL
        """
        
        params = []
        if not incluir_todos:
            query += " AND date(data_ap) BETWEEN ? AND ?"
            params = [data_inicio.isoformat(), data_fim.isoformat()]
        
        query += " GROUP BY mes, vacina ORDER BY mes"
        
        df_tendencia = self.db.read_sql(query, params)

        if not df_tendencia.empty:
            fig = px.line(
                df_tendencia,
                x='mes',
                y='total_doses',
                color='vacina',
                title='Tendência de Vacinação por Mês',
                markers=True,
                labels={'mes': 'Mês/Ano', 'total_doses': 'Número de Doses', 'vacina': 'Vacina'}
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

            pivot = df_tendencia.pivot_table(
                index='mes',
                columns='vacina',
                values='total_doses',
                aggfunc='sum',
                fill_value=0
            )

            st.subheader("📊 Tabela de Dados")
            st.dataframe(pivot, use_container_width=True)

            st.subheader("📈 Estatísticas")

            col_stat1, col_stat2, col_stat3 = st.columns(3)

            with col_stat1:
                total_meses = df_tendencia['mes'].nunique()
                st.metric("Meses Analisados", total_meses)

            with col_stat2:
                total_vacinas = df_tendencia['vacina'].nunique()
                st.metric("Vacinas Diferentes", total_vacinas)

            with col_stat3:
                media_mensal = df_tendencia.groupby('mes')['total_doses'].sum().mean()
                st.metric("Média Mensal", f"{media_mensal:.0f}")

            vacina_top = df_tendencia.groupby('vacina')['total_doses'].sum().idxmax()
            total_top = df_tendencia.groupby('vacina')['total_doses'].sum().max()
            st.info(f"**Vacina mais aplicada:** {vacina_top} ({total_top:,} doses)")
        else:
            st.info("📭 Dados insuficientes para análise de tendência.")
    
    def _render_demografico(self, data_inicio, data_fim, incluir_todos):
        """Renderiza análise demográfica"""
        st.subheader("👥 Análise Demográfica")

        # Query para buscar dados com filtro de data
        query = """
            SELECT
                s.id_comp,
                s.sexo,
                s.superintendencia,
                s.data_nascimento,
                CASE WHEN d.id_comp IS NOT NULL THEN 1 ELSE 0 END as vacinado
            FROM servidores s
            LEFT JOIN doses d ON s.id_comp = d.id_comp
        """
        
        if not incluir_todos:
            query += " AND date(d.data_ap) BETWEEN ? AND ?"
        
        query += " WHERE s.situacao_funcional = 'ATIVO'"
        
        params = []
        if not incluir_todos:
            params = [data_inicio.isoformat(), data_fim.isoformat()]
        
        df = self.db.read_sql(query, params)
        
        if not df.empty:
            # Calcula idade em Python
            from datetime import date
            hoje = date.today()
            
            def calcular_idade(data_nasc):
                if pd.isna(data_nasc) or data_nasc is None or data_nasc == '':
                    return None
                try:
                    if isinstance(data_nasc, str):
                        nasc = pd.to_datetime(data_nasc).date()
                    else:
                        nasc = data_nasc
                    
                    idade = hoje.year - nasc.year
                    if (hoje.month, hoje.day) < (nasc.month, nasc.day):
                        idade -= 1
                    return idade
                except Exception:
                    return None
            
            def classificar_faixa(idade):
                if idade is None:
                    return 'Não informado'
                if idade < 20:
                    return 'Menos de 20'
                elif idade < 30:
                    return '20-29'
                elif idade < 40:
                    return '30-39'
                elif idade < 50:
                    return '40-49'
                elif idade < 60:
                    return '50-59'
                else:
                    return '60 ou mais'
            
            # Aplica os cálculos
            df['idade'] = df['data_nascimento'].apply(calcular_idade)
            df['faixa_etaria'] = df['idade'].apply(classificar_faixa)
            
            # Agrupamento
            df_demo = df.groupby(['sexo', 'superintendencia', 'faixa_etaria'], as_index=False).agg(
                total_servidores=('id_comp', 'count'),
                servidores_vacinados=('vacinado', 'sum')
            )
            
            st.subheader("📊 Cobertura por Superintendência")
            
            df_super = df.groupby('superintendencia', as_index=False).agg(
                total_servidores=('id_comp', 'count'),
                servidores_vacinados=('vacinado', 'sum')
            )
            
            df_super['cobertura'] = (df_super['servidores_vacinados'] / df_super['total_servidores'] * 100).round(1)
            df_super = df_super.sort_values('cobertura', ascending=False)
            
            fig_super = px.bar(
                df_super.head(10),
                x='superintendencia',
                y='cobertura',
                title='Top 10 - Cobertura Vacinal por Superintendência',
                labels={'cobertura': 'Cobertura (%)', 'superintendencia': 'Superintendência'},
                color='cobertura',
                color_continuous_scale='viridis',
                text='cobertura'
            )
            fig_super.update_traces(texttemplate='%{text}%', textposition='outside')
            fig_super.update_layout(height=450)
            st.plotly_chart(fig_super, use_container_width=True)
            
            st.subheader("👥 Distribuição por Sexo e Faixa Etária")
            
            df_faixa = df_demo[df_demo['faixa_etaria'] != 'Não informado'].copy()
            
            if not df_faixa.empty:
                fig = px.bar(
                    df_faixa,
                    x='faixa_etaria',
                    y='servidores_vacinados',
                    color='sexo',
                    barmode='group',
                    title='Servidores Vacinados por Sexo e Faixa Etária',
                    labels={'servidores_vacinados': 'Servidores Vacinados', 'faixa_etaria': 'Faixa Etária'},
                    category_orders={'faixa_etaria': ['Menos de 20', '20-29', '30-39', '40-49', '50-59', '60 ou mais']}
                )
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📭 Dados de idade não disponíveis para gerar gráfico por faixa etária.")

            # Mostra a tabela completa
            st.dataframe(
                df_demo,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "sexo": "Sexo",
                    "superintendencia": "Superintendência",
                    "faixa_etaria": "Faixa Etária",
                    "total_servidores": "Total Servidores",
                    "servidores_vacinados": "Vacinados"
                }
            )
            
            # Estatísticas adicionais
            st.subheader("📊 Estatísticas Demográficas")
            col_est1, col_est2, col_est3 = st.columns(3)
            
            with col_est1:
                total_com_idade = len(df[df['idade'].notna()])
                st.metric("Servidores com Idade Informada", f"{total_com_idade:,}")
            
            with col_est2:
                idade_media = df['idade'].mean()
                st.metric("Idade Média", f"{idade_media:.1f} anos" if not pd.isna(idade_media) else "N/A")
            
            with col_est3:
                total_vacinados = int(df['vacinado'].sum())
                st.metric("Total Vacinados", f"{total_vacinados:,}")
            
        else:
            st.info("📭 Dados insuficientes para análise demográfica.")
    
    def _render_eficiencia(self, data_inicio, data_fim, incluir_todos):
        """Renderiza análise de eficiência"""
        st.subheader("💉 Eficiência de Vacinas")
        
        # Query para análise de eficiência por vacina com filtro de data
        query = """
            SELECT 
                vacina,
                COUNT(*) as total_doses,
                COUNT(DISTINCT id_comp) as total_pessoas,
                COUNT(CASE WHEN data_ret IS NOT NULL AND data_ret > date('now') THEN 1 END) as doses_futuras,
                MIN(data_ap) as primeira_dose,
                MAX(data_ap) as ultima_dose
            FROM doses
        """
        
        params = []
        if not incluir_todos:
            query += " WHERE date(data_ap) BETWEEN ? AND ?"
            params = [data_inicio.isoformat(), data_fim.isoformat()]
        
        query += " GROUP BY vacina ORDER BY total_doses DESC"
        
        df_eficiencia = self.db.read_sql(query, params)
        
        if not df_eficiencia.empty:
            # Calcula métricas adicionais
            df_eficiencia['media_doses_por_pessoa'] = (df_eficiencia['total_doses'] / df_eficiencia['total_pessoas']).round(2)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.pie(
                    df_eficiencia.head(8),
                    values='total_doses',
                    names='vacina',
                    title='Distribuição de Doses por Vacina (Top 8)'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    df_eficiencia.head(10),
                    x='vacina',
                    y='media_doses_por_pessoa',
                    title='Média de Doses por Pessoa',
                    labels={'media_doses_por_pessoa': 'Média de Doses', 'vacina': 'Vacina'},
                    color='media_doses_por_pessoa',
                    color_continuous_scale='blues',
                    text='media_doses_por_pessoa'
                )
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("📋 Tabela de Eficiência")
            st.dataframe(
                df_eficiencia,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "vacina": "Vacina",
                    "total_doses": "Total de Doses",
                    "total_pessoas": "Pessoas Vacinadas",
                    "media_doses_por_pessoa": "Média Doses/Pessoa",
                    "doses_futuras": "Doses Futuras",
                    "primeira_dose": "Primeira Aplicação",
                    "ultima_dose": "Última Aplicação"
                }
            )
        else:
            st.info("📭 Dados insuficientes para análise de eficiência.")
    
    def _render_metas(self, data_inicio, data_fim, incluir_todos):
        """Renderiza acompanhamento de metas"""
        st.subheader("🎯 Metas e Objetivos")
        
        # Busca dados para metas
        total_servidores = self.db.fetchone("SELECT COUNT(*) as total FROM servidores WHERE situacao_funcional = 'ATIVO'")
        total_vacinados = self.db.fetchone("SELECT COUNT(DISTINCT id_comp) as total FROM doses")
        
        if not incluir_todos:
            # Filtrar vacinados no período
            total_vacinados_periodo = self.db.fetchone(
                "SELECT COUNT(DISTINCT id_comp) as total FROM doses WHERE date(data_ap) BETWEEN ? AND ?",
                (data_inicio.isoformat(), data_fim.isoformat())
            )
            total_vacinados_periodo = total_vacinados_periodo['total'] if total_vacinados_periodo else 0
        else:
            total_vacinados_periodo = total_vacinados['total'] if total_vacinados else 0
        
        total_doses = self.db.fetchone("SELECT COUNT(*) as total FROM doses")
        
        total_serv = int(total_servidores['total']) if total_servidores else 0
        total_vac = int(total_vacinados['total']) if total_vacinados else 0
        total_dos = int(total_doses['total']) if total_doses else 0
        
        cobertura_atual = (total_vac / total_serv * 100) if total_serv > 0 else 0
        cobertura_periodo = (total_vacinados_periodo / total_serv * 100) if total_serv > 0 else 0
        
        # Métricas principais
        col_meta1, col_meta2, col_meta3, col_meta4 = st.columns(4)
        
        with col_meta1:
            st.metric("Meta de Cobertura", "80%", f"{cobertura_atual:.1f}% atual")
        
        with col_meta2:
            st.metric("Servidores Ativos", f"{total_serv:,}")
        
        with col_meta3:
            st.metric("Servidores Vacinados", f"{total_vac:,}")
        
        with col_meta4:
            st.metric("Total de Doses", f"{total_dos:,}")
        
        # Gráfico de progresso
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Meta',
            x=['Cobertura'],
            y=[80],
            marker_color='#FFA07A',
            text=['80%'],
            textposition='outside'
        ))
        
        fig.add_trace(go.Bar(
            name='Atual',
            x=['Cobertura'],
            y=[cobertura_atual],
            marker_color='#90EE90',
            text=[f'{cobertura_atual:.1f}%'],
            textposition='outside'
        ))
        
        if not incluir_todos:
            fig.add_trace(go.Bar(
                name='No Período',
                x=['Cobertura'],
                y=[cobertura_periodo],
                marker_color='#87CEEB',
                text=[f'{cobertura_periodo:.1f}%'],
                textposition='outside'
            ))
        
        fig.update_layout(
            title='Progresso da Meta de Cobertura (80%)',
            xaxis_title='',
            yaxis_title='Cobertura (%)',
            yaxis=dict(range=[0, 100]),
            barmode='group',
            height=450
        )
        
        fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Meta 80%")
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Servidores pendentes
        servidores_pendentes = total_serv - total_vac
        st.info(f"**Servidores pendentes de vacinação:** {servidores_pendentes:,}")
        
        if servidores_pendentes > 0:
            st.warning(f"⚠️ Faltam {servidores_pendentes:,} servidores para atingir a meta de 80% de cobertura!")
            
            # Calcular quantos precisam ser vacinados por mês para atingir a meta
            from dateutil.relativedelta import relativedelta
            
            if cobertura_atual < 80:
                faltam = int(0.8 * total_serv - total_vac)
                st.metric("Servidores que precisam ser vacinados", f"{faltam:,}")
        else:
            st.success("🎉 Meta de cobertura atingida!")
    
    def _gerar_pdf_completo(self, data_inicio, data_fim, incluir_todos):
        """Gera um PDF completo com todos os gráficos e análises"""
        
        if not REPORTLAB_AVAILABLE:
            st.error("❌ Biblioteca reportlab não instalada. Execute: pip install reportlab")
            return
        
        with st.spinner("🔄 Gerando relatório PDF completo... Isso pode levar alguns segundos."):
            try:
                # Criar buffer para o PDF
                pdf_buffer = io.BytesIO()
                
                # Configurar o documento
                doc = SimpleDocTemplate(
                    pdf_buffer,
                    pagesize=A4,
                    rightMargin=2*cm,
                    leftMargin=2*cm,
                    topMargin=2*cm,
                    bottomMargin=2*cm
                )
                
                # Lista de elementos do PDF
                elements = []
                
                # Estilos
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=18,
                    alignment=TA_CENTER,
                    spaceAfter=12,
                    textColor=colors.HexColor('#1e3a8a')
                )
                
                subtitle_style = ParagraphStyle(
                    'CustomSubtitle',
                    parent=styles['Heading2'],
                    fontSize=14,
                    alignment=TA_LEFT,
                    spaceAfter=8,
                    spaceBefore=12,
                    textColor=colors.HexColor('#3b82f6')
                )
                
                normal_style = styles['Normal']
                normal_style.fontSize = 10
                
                # Cabeçalho
                elements.append(Paragraph("NASST Digital - Relatório Avançado de Vacinação", title_style))
                elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
                elements.append(Paragraph(f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}", normal_style))
                elements.append(Spacer(1, 0.5*cm))
                
                # Métricas gerais
                elements.append(Paragraph("📊 Métricas Gerais", subtitle_style))
                
                # Buscar métricas
                total_servidores = self.db.fetchone("SELECT COUNT(*) as total FROM servidores WHERE situacao_funcional = 'ATIVO'")
                total_serv = int(total_servidores['total']) if total_servidores else 0
                
                total_vacinados = self.db.fetchone("SELECT COUNT(DISTINCT id_comp) as total FROM doses")
                total_vac = int(total_vacinados['total']) if total_vacinados else 0
                
                total_doses = self.db.fetchone("SELECT COUNT(*) as total FROM doses")
                total_dos = int(total_doses['total']) if total_doses else 0
                
                cobertura = (total_vac / total_serv * 100) if total_serv > 0 else 0
                
                # Tabela de métricas
                metricas_data = [
                    ['Métrica', 'Valor'],
                    ['Servidores Ativos', f"{total_serv:,}"],
                    ['Servidores Vacinados', f"{total_vac:,}"],
                    ['Total de Doses', f"{total_dos:,}"],
                    ['Cobertura Geral', f"{cobertura:.1f}%"]
                ]
                
                metricas_table = Table(metricas_data, colWidths=[8*cm, 6*cm])
                metricas_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#3b82f6')),
                    ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f9ff')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                ]))
                
                elements.append(metricas_table)
                elements.append(Spacer(1, 0.5*cm))
                
                # Gráfico de cobertura por superintendência
                elements.append(Paragraph("🏢 Cobertura por Superintendência", subtitle_style))
                
                # Query para superintendências
                df_super = self.db.read_sql("""
                    SELECT 
                        s.superintendencia,
                        COUNT(DISTINCT s.id_comp) as total_servidores,
                        COUNT(DISTINCT d.id_comp) as servidores_vacinados
                    FROM servidores s
                    LEFT JOIN doses d ON s.id_comp = d.id_comp
                    WHERE s.situacao_funcional = 'ATIVO'
                      AND s.superintendencia IS NOT NULL
                      AND s.superintendencia != ''
                    GROUP BY s.superintendencia
                    HAVING total_servidores > 0
                    ORDER BY servidores_vacinados DESC
                    LIMIT 10
                """)
                
                if not df_super.empty:
                    df_super['percentual'] = (df_super['servidores_vacinados'] / df_super['total_servidores'] * 100).round(1)
                    
                    # Criar tabela para PDF
                    super_data = [['Superintendência', 'Total', 'Vacinados', '%']]
                    for _, row in df_super.head(10).iterrows():
                        super_data.append([
                            row['superintendencia'][:30],
                            str(row['total_servidores']),
                            str(row['servidores_vacinados']),
                            f"{row['percentual']}%"
                        ])
                    
                    super_table = Table(super_data, colWidths=[6*cm, 2.5*cm, 2.5*cm, 2*cm])
                    super_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f9ff')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                    ]))
                    
                    elements.append(super_table)
                
                elements.append(Spacer(1, 0.5*cm))
                
                # Dados de tendência temporal
                elements.append(Paragraph("📅 Tendência Temporal", subtitle_style))
                
                query_tendencia = """
                    SELECT strftime('%Y-%m', data_ap) AS mes,
                           COUNT(*) AS total_doses
                    FROM doses
                    WHERE data_ap IS NOT NULL
                    GROUP BY mes
                    ORDER BY mes DESC
                    LIMIT 12
                """
                
                df_tendencia = self.db.read_sql(query_tendencia)
                
                if not df_tendencia.empty:
                    tendencia_data = [['Mês', 'Total de Doses']]
                    for _, row in df_tendencia.iterrows():
                        tendencia_data.append([row['mes'], str(row['total_doses'])])
                    
                    tendencia_table = Table(tendencia_data, colWidths=[4*cm, 4*cm])
                    tendencia_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0f9ff')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
                    ]))
                    
                    elements.append(tendencia_table)
                
                # Rodapé
                elements.append(Spacer(1, 1*cm))
                elements.append(Paragraph(
                    "Documento gerado eletronicamente pelo sistema NASST Digital.",
                    normal_style
                ))
                
                # Gerar PDF
                doc.build(elements)
                
                # Oferecer download
                pdf_buffer.seek(0)
                
                st.download_button(
                    label="📥 Baixar Relatório PDF",
                    data=pdf_buffer,
                    file_name=f"relatorio_avancado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                st.success("✅ PDF gerado com sucesso!")
                
            except Exception as e:
                st.error(f"❌ Erro ao gerar PDF: {str(e)}")
                import traceback
                traceback.print_exc()