"""
relatorio_service.py - Serviços de relatórios e dashboards
"""

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF

from core.security import Formatters


class RelatoriosService:
    def __init__(self, db: "Database") -> None:
        self.db = db

    def get_metricas_gerais(self) -> Dict[str, Any]:
        metricas: Dict[str, Any] = {}
        total_servidores = self.db.fetchone("SELECT COUNT(*) AS c FROM servidores WHERE situacao_funcional = 'ATIVO'")
        metricas["total_servidores"] = int(total_servidores["c"]) if total_servidores else 0

        total_doses = self.db.fetchone("SELECT COUNT(*) AS c FROM doses")
        metricas["total_doses"] = int(total_doses["c"]) if total_doses else 0

        vacinados = self.db.fetchone("SELECT COUNT(DISTINCT id_comp) AS c FROM doses")
        servidores_vacinados = int(vacinados["c"]) if vacinados else 0
        metricas["cobertura"] = (servidores_vacinados / metricas["total_servidores"] * 100) if metricas["total_servidores"] else 0.0

        return metricas

    def grafico_cobertura_lotacao_top10(self) -> Optional[go.Figure]:
        df = self.db.read_sql(
            """
            SELECT s.lotacao,
                   COUNT(DISTINCT s.id_comp) AS total_servidores,
                   COUNT(DISTINCT d.id_comp) AS servidores_vacinados
            FROM servidores s
            LEFT JOIN doses d ON s.id_comp = d.id_comp
            WHERE s.situacao_funcional = 'ATIVO'
            GROUP BY s.lotacao
            HAVING total_servidores > 0
            ORDER BY total_servidores DESC
            LIMIT 10
            """
        )
        if df.empty:
            return None

        df["cobertura"] = (df["servidores_vacinados"] / df["total_servidores"] * 100).round(1)

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Total Servidores", x=df["lotacao"], y=df["total_servidores"]))
        fig.add_trace(go.Bar(name="Vacinados", x=df["lotacao"], y=df["servidores_vacinados"]))
        fig.add_trace(
            go.Scatter(
                name="% Cobertura",
                x=df["lotacao"],
                y=df["cobertura"],
                yaxis="y2",
                mode="lines+markers",
            )
        )
        fig.update_layout(
            title="Cobertura Vacinal por Lotacao (Top 10)",
            barmode="group",
            yaxis=dict(title="Quantidade de Servidores"),
            yaxis2=dict(title="% Cobertura", overlaying="y", side="right", range=[0, 100]),
            hovermode="x unified",
            height=420,
        )
        return fig

    def grafico_cobertura_superintendencia_top10(self) -> Optional[go.Figure]:
        """Gráfico de cobertura vacinal por superintendência (Top 10)"""
        df = self.db.read_sql(
            """
            SELECT s.superintendencia,
                   COUNT(DISTINCT s.id_comp) AS total_servidores,
                   COUNT(DISTINCT d.id_comp) AS servidores_vacinados
            FROM servidores s
            LEFT JOIN doses d ON s.id_comp = d.id_comp
            WHERE s.situacao_funcional = 'ATIVO'
              AND s.superintendencia IS NOT NULL
              AND s.superintendencia != ''
            GROUP BY s.superintendencia
            HAVING total_servidores > 0
            ORDER BY total_servidores DESC
            LIMIT 10
            """
        )
        if df.empty:
            return None

        df["cobertura"] = (df["servidores_vacinados"] / df["total_servidores"] * 100).round(1)

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Total Servidores", x=df["superintendencia"], y=df["total_servidores"]))
        fig.add_trace(go.Bar(name="Vacinados", x=df["superintendencia"], y=df["servidores_vacinados"]))
        fig.add_trace(
            go.Scatter(
                name="% Cobertura",
                x=df["superintendencia"],
                y=df["cobertura"],
                yaxis="y2",
                mode="lines+markers",
                line=dict(color='red', width=2),
            )
        )
        fig.update_layout(
            title="Cobertura Vacinal por Superintendência (Top 10)",
            barmode="group",
            yaxis=dict(title="Quantidade de Servidores"),
            yaxis2=dict(title="% Cobertura", overlaying="y", side="right", range=[0, 100]),
            hovermode="x unified",
            height=420,
        )
        return fig

    def doses_ultimos_6_meses(self) -> pd.DataFrame:
        return self.db.read_sql(
            """
            SELECT strftime('%Y-%m', data_ap) AS mes,
                   COUNT(*) AS total_doses,
                   vacina
            FROM doses
            WHERE data_ap >= date('now', '-6 months')
            GROUP BY mes, vacina
            ORDER BY mes
            """
        )

    def cobertura_detalhada_por_superintendencia(self, superintendencia: str, data_ini: date, data_fim: date) -> pd.DataFrame:
        """Relatório detalhado de cobertura por superintendência"""
        params: List[Any] = []
        where = "WHERE s.situacao_funcional = 'ATIVO' "
        if superintendencia != "TODAS":
            where += "AND s.superintendencia = ? "
            params.append(superintendencia)

        params.extend([data_ini.isoformat(), data_fim.isoformat()])

        df = self.db.read_sql(
            f"""
            SELECT
                s.superintendencia,
                COUNT(DISTINCT s.id_comp) AS total_servidores,
                COUNT(DISTINCT CASE WHEN d.data_ap BETWEEN ? AND ? THEN s.id_comp END) AS vacinados_periodo,
                COUNT(DISTINCT d.id_comp) AS total_vacinados
            FROM servidores s
            LEFT JOIN doses d ON s.id_comp = d.id_comp
            {where}
            GROUP BY s.superintendencia
            ORDER BY total_servidores DESC
            """,
            tuple(params),
        )
        return df

    def cobertura_por_superintendencia_lotacao(self, superintendencia: str) -> pd.DataFrame:
        """Detalhamento de cobertura por lotação dentro de uma superintendência"""
        params = []
        where = "WHERE s.situacao_funcional = 'ATIVO' "
        if superintendencia != "TODAS":
            where += "AND s.superintendencia = ? "
            params.append(superintendencia)

        df = self.db.read_sql(
            f"""
            SELECT
                s.lotacao,
                s.superintendencia,
                COUNT(DISTINCT s.id_comp) AS total_servidores,
                COUNT(DISTINCT d.id_comp) AS servidores_vacinados,
                ROUND((COUNT(DISTINCT d.id_comp) * 100.0 / COUNT(DISTINCT s.id_comp)), 1) AS cobertura_percentual
            FROM servidores s
            LEFT JOIN doses d ON s.id_comp = d.id_comp
            {where}
            GROUP BY s.lotacao, s.superintendencia
            HAVING total_servidores > 0
            ORDER BY total_servidores DESC
            """,
            tuple(params)
        )
        return df

    def cobertura_detalhada(self, lotacao: str, data_ini: date, data_fim: date) -> pd.DataFrame:
        params: List[Any] = []
        where = "WHERE s.situacao_funcional = 'ATIVO' "
        if lotacao != "TODAS":
            where += "AND s.lotacao = ? "
            params.append(lotacao)

        params.extend([data_ini.isoformat(), data_fim.isoformat()])

        df = self.db.read_sql(
            f"""
            SELECT
                s.lotacao,
                COUNT(DISTINCT s.id_comp) AS total_servidores,
                COUNT(DISTINCT CASE WHEN d.data_ap BETWEEN ? AND ? THEN s.id_comp END) AS vacinados_periodo,
                COUNT(DISTINCT d.id_comp) AS total_vacinados
            FROM servidores s
            LEFT JOIN doses d ON s.id_comp = d.id_comp
            {where}
            GROUP BY s.lotacao
            ORDER BY total_servidores DESC
            """,
            tuple(params),
        )

        if df.empty:
            return df

        df["cobertura_periodo"] = (df["vacinados_periodo"] / df["total_servidores"] * 100).round(1)
        df["cobertura_total"] = (df["total_vacinados"] / df["total_servidores"] * 100).round(1)
        return df

    def tendencia_temporal(self) -> pd.DataFrame:
        return self.db.read_sql(
            """
            SELECT strftime('%Y-%m', data_ap) AS mes,
                   COUNT(*) AS total_doses,
                   vacina
            FROM doses
            WHERE data_ap IS NOT NULL
            GROUP BY mes, vacina
            ORDER BY mes
            """
        )


class RelatoriosGerenciaisService:
    def __init__(self, db: "Database") -> None:
        self.db = db

    def gerar_relatorio_servidor(self, id_comp: str) -> Dict[str, Any]:
        servidor = self.db.fetchone(
            """
            SELECT * FROM servidores WHERE id_comp = ?
            """,
            (id_comp,)
        )
        
        if not servidor:
            return {}
        
        servidor_dict = dict(servidor)
        
        historico = self.db.read_sql(
            """
            SELECT d.*, c.nome_campanha
            FROM doses d
            LEFT JOIN campanhas c ON d.campanha_id = c.id
            WHERE d.id_comp = ?
            ORDER BY d.data_ap DESC
            """,
            (id_comp,)
        )
        
        idade = Formatters.calcular_idade(servidor_dict.get("data_nascimento"))
        
        return {
            "servidor": servidor_dict,
            "historico_vacinacao": historico.to_dict('records') if not historico.empty else [],
            "idade": idade,
            "total_doses": len(historico),
            "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }

    def gerar_relatorio_cobertura_geral(self) -> Dict[str, Any]:
        total_servidores = self.db.fetchone(
            "SELECT COUNT(*) as total FROM servidores WHERE situacao_funcional = 'ATIVO'"
        )
        total_vacinados = self.db.fetchone(
            "SELECT COUNT(DISTINCT id_comp) as total FROM doses"
        )
        total_doses = self.db.fetchone("SELECT COUNT(*) as total FROM doses")
        
        cobertura_lotacao = self.db.read_sql(
            """
            SELECT 
                s.lotacao,
                COUNT(DISTINCT s.id_comp) as total_servidores,
                COUNT(DISTINCT d.id_comp) as servidores_vacinados,
                ROUND((COUNT(DISTINCT d.id_comp) * 100.0 / COUNT(DISTINCT s.id_comp)), 1) as cobertura_percentual
            FROM servidores s
            LEFT JOIN doses d ON s.id_comp = d.id_comp
            WHERE s.situacao_funcional = 'ATIVO'
            GROUP BY s.lotacao
            HAVING total_servidores > 0
            ORDER BY cobertura_percentual DESC
            """
        )
        
        cobertura_vacina = self.db.read_sql(
            """
            SELECT 
                vacina,
                COUNT(*) as total_doses,
                COUNT(DISTINCT id_comp) as servidores_vacinados
            FROM doses
            GROUP BY vacina
            ORDER BY total_doses DESC
            """
        )
        
        doses_mensais = self.db.read_sql(
            """
            SELECT 
                strftime('%Y-%m', data_ap) as mes,
                COUNT(*) as total_doses
            FROM doses
            WHERE data_ap >= date('now', '-12 months')
            GROUP BY mes
            ORDER BY mes
            """
        )
        
        return {
            "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "totais": {
                "servidores_ativos": int(total_servidores["total"]) if total_servidores else 0,
                "servidores_vacinados": int(total_vacinados["total"]) if total_vacinados else 0,
                "total_doses": int(total_doses["total"]) if total_doses else 0,
                "cobertura_geral": round((int(total_vacinados["total"]) * 100.0 / int(total_servidores["total"])), 1) 
                    if total_servidores and total_vacinados and int(total_servidores["total"]) > 0 else 0
            },
            "cobertura_lotacao": cobertura_lotacao.to_dict('records'),
            "cobertura_vacina": cobertura_vacina.to_dict('records'),
            "doses_mensais": doses_mensais.to_dict('records'),
            "periodo_analise": "Ultimos 12 meses"
        }

    def gerar_relatorio_campanhas(self) -> Dict[str, Any]:
        campanhas = self.db.read_sql(
            """
            SELECT 
                c.*,
                COUNT(d.id) as doses_aplicadas,
                COUNT(DISTINCT d.id_comp) as servidores_atendidos
            FROM campanhas c
            LEFT JOIN doses d ON c.id = d.campanha_id
            GROUP BY c.id
            ORDER BY c.data_inicio DESC
            """
        )
        
        stats_status = self.db.read_sql(
            """
            SELECT 
                status,
                COUNT(*) as total_campanhas,
                SUM(doses_aplicadas) as total_doses
            FROM (
                SELECT 
                    c.*,
                    COUNT(d.id) as doses_aplicadas
                FROM campanhas c
                LEFT JOIN doses d ON c.id = d.campanha_id
                GROUP BY c.id
            )
            GROUP BY status
            """
        )
        
        return {
            "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "total_campanhas": len(campanhas),
            "campanhas": campanhas.to_dict('records'),
            "estatisticas_status": stats_status.to_dict('records')
        }


class RelatorioPDFService:
    """Servico de geracao de relatorios PDF"""
    
    @staticmethod
    def _parse_date(value):
        return Formatters.parse_date(value)

    @staticmethod
    def _calcular_idade(data):
        idade = Formatters.calcular_idade(data)
        return f"{idade} anos" if idade is not None else "Não informada"

    @staticmethod
    def _calcular_tempo_servico(data):
        return Formatters.calcular_tempo_servico(data)

    @staticmethod
    def _formatar_cpf(cpf):
        return Formatters.formatar_cpf(cpf)

    @staticmethod
    def _formatar_data(data):
        return Formatters.formatar_data_br(data) or "Não informado"

    @staticmethod
    def gerar_ficha_cadastral_pdf(logo_path, servidor: dict, historico_vacinacao: list) -> bytes:
        """Gera ficha cadastral do servidor em PDF"""
        pdf = FPDF()
        pdf.add_page()
        
        # CABECALHO
        if logo_path and os.path.exists(logo_path):
            pdf.image(logo_path, 10, 8, 20)
        
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "NASST DIGITAL", 0, 1, "C")
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, "Ficha Cadastral do Servidor", 0, 1, "C")
        pdf.ln(5)

        # 1. IDENTIFICACAO
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 7, "1. IDENTIFICACAO DO SERVIDOR", 0, 1, "L", 1)
        pdf.ln(2)
        
        # NOME
        pdf.set_font("Arial", "B", 10)
        pdf.cell(20, 6, "Nome:", 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, servidor.get("nome", "Nao informado"), 0, 1)
        
        # CPF e MATRICULA
        pdf.set_font("Arial", "B", 10)
        pdf.cell(20, 6, "CPF:", 0, 0)
        pdf.set_font("Arial", "", 10)
        cpf = servidor.get("cpf", "Nao informado")
        if cpf and len(str(cpf)) == 11:
            cpf = f"{str(cpf)[:3]}.{str(cpf)[3:6]}.{str(cpf)[6:9]}-{str(cpf)[9:]}"
        pdf.cell(70, 6, str(cpf), 0, 0)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "Matricula:", 0, 0)
        pdf.set_font("Arial", "", 10)
        matricula = f"{servidor.get('numfunc', '')}-{servidor.get('numvinc', '')}"
        if matricula == "-":
            matricula = servidor.get("id_comp", "Nao informado")
        pdf.cell(0, 6, matricula, 0, 1)
        
        # DATA NASCIMENTO e IDADE
        pdf.set_font("Arial", "B", 10)
        pdf.cell(20, 6, "Nasc:", 0, 0)
        pdf.set_font("Arial", "", 10)
        
        data_nasc = servidor.get("data_nascimento")
        data_nasc_str = Formatters.formatar_data_br(data_nasc) or "Não informado"
        idade = Formatters.calcular_idade(data_nasc)
        idade_str = f"{idade} anos" if idade is not None else "Não informada"
        
        pdf.cell(70, 6, data_nasc_str, 0, 0)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "Idade:", 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, idade_str, 0, 1)
        
        # SEXO
        pdf.set_font("Arial", "B", 10)
        pdf.cell(20, 6, "Sexo:", 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, servidor.get("sexo", "Nao informado"), 0, 1)
        pdf.ln(3)

        # 2. DADOS FUNCIONAIS
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 7, "2. DADOS FUNCIONAIS", 0, 1, "L", 1)
        pdf.ln(2)
        
        # CARGO
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "Cargo:", 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, servidor.get("cargo", "Nao informado"), 0, 1)
        
        # LOTACAO
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "Lotacao:", 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, servidor.get("lotacao", "Nao informado"), 0, 1)
        
        # LOCAL FISICO
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "Local Fisico:", 0, 0)
        pdf.set_font("Arial", "", 10)
        local = servidor.get("lotacao_fisica", "Nao informado")
        if local in [None, "None", ""]:
            local = "Nao informado"
        pdf.cell(0, 6, str(local), 0, 1)
        
        # VINCULO e SITUACAO
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "Vinculo:", 0, 0)
        pdf.set_font("Arial", "", 10)
        vinculo = servidor.get("tipo_vinculo", "Nao informado")
        if vinculo in [None, "None", ""]:
            vinculo = "Nao informado"
        pdf.cell(70, 6, str(vinculo), 0, 0)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "Situacao:", 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, servidor.get("situacao_funcional", "ATIVO"), 0, 1)
        
        # ADMISSAO e TEMPO
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "Admissao:", 0, 0)
        pdf.set_font("Arial", "", 10)
        
        data_adm = servidor.get("data_admissao")
        data_adm_str = Formatters.formatar_data_br(data_adm) or "Não informado"
        tempo_str = Formatters.calcular_tempo_servico(data_adm)
        
        pdf.cell(70, 6, data_adm_str, 0, 0)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "Tempo:", 0, 0)
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, tempo_str, 0, 1)
        pdf.ln(3)

        # 3. CONTATOS
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 7, "3. CONTATOS", 0, 1, "L", 1)
        pdf.ln(2)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "Telefone:", 0, 0)
        pdf.set_font("Arial", "", 10)
        fone = servidor.get("telefone", "Nao informado")
        if fone in [None, "None", ""]:
            fone = "Nao informado"
        pdf.cell(0, 6, str(fone), 0, 1)
        
        pdf.set_font("Arial", "B", 10)
        pdf.cell(25, 6, "E-mail:", 0, 0)
        pdf.set_font("Arial", "", 10)
        email = servidor.get("email", "Nao informado")
        if email in [None, "None", ""]:
            email = "Nao informado"
        pdf.cell(0, 6, str(email), 0, 1)
        pdf.ln(3)

        # 4. HISTORICO VACINAL
        pdf.set_font("Arial", "B", 12)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(0, 7, "4. HISTORICO VACINAL", 0, 1, "L", 1)
        pdf.ln(2)
        
        if not historico_vacinacao:
            pdf.set_font("Arial", "I", 10)
            pdf.cell(0, 6, "Nenhum registro de vacinacao encontrado para este servidor.", 0, 1, "C")
        else:
            # Cabeçalho da tabela
            pdf.set_font("Arial", "B", 9)
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(60, 6, "Vacina", 1, 0, "C", 1)
            pdf.cell(30, 6, "Dose", 1, 0, "C", 1)
            pdf.cell(45, 6, "Data Aplicacao", 1, 0, "C", 1)
            pdf.cell(45, 6, "Proximo", 1, 1, "C", 1)
            
            # Dados
            pdf.set_font("Arial", "", 8)
            
            for i, v in enumerate(historico_vacinacao):
                # Verificar se precisa de nova página (a cada 25 linhas aproximadamente)
                if i > 0 and i % 25 == 0:
                    pdf.add_page()
                    # Reimprimir cabeçalho na nova página
                    pdf.set_font("Arial", "B", 9)
                    pdf.set_fill_color(200, 200, 200)
                    pdf.cell(60, 6, "Vacina", 1, 0, "C", 1)
                    pdf.cell(30, 6, "Dose", 1, 0, "C", 1)
                    pdf.cell(45, 6, "Data Aplicacao", 1, 0, "C", 1)
                    pdf.cell(45, 6, "Proximo", 1, 1, "C", 1)
                    pdf.set_font("Arial", "", 8)
                
                # Linha de dados
                pdf.cell(60, 5, str(v.get("vacina", ""))[:20], 1)
                pdf.cell(30, 5, str(v.get("dose", ""))[:8], 1, 0, "C")
                
                da = Formatters.formatar_data_br(v.get("data_ap"))
                pdf.cell(45, 5, da if da else "-", 1, 0, "C")
                
                dr = Formatters.formatar_data_br(v.get("data_ret"))
                pdf.cell(45, 5, dr if dr else "-", 1, 1, "C")

        # RODAPE
        pdf.set_y(260)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 5, f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1, "R")
        pdf.cell(0, 5, "Documento gerado eletronicamente pelo sistema NASST Digital.", 0, 1, "C")

        return bytes(pdf.output(dest="S"))