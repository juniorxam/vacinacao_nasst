"""
whatsapp_service.py - Serviço de notificação via WhatsApp
"""

import urllib.parse
import pandas as pd
from typing import List, Dict, Any, Optional
import streamlit as st


class WhatsAppService:
    """
    Serviço para envio de notificações via WhatsApp
    """
    
    # Template de mensagem para campanhas
    TEMPLATE_CAMPANHA = """
🏥 *CAMPANHA DE VACINAÇÃO* 🏥

Olá *{nome}*,

A Secretaria de Saúde informa sobre a campanha:

📅 *{nome_campanha}*
💉 *Vacina:* {vacina}
📆 *Período:* {data_inicio} a {data_fim}
📍 *Local:* {local}

📋 *Público-alvo:* {publico_alvo}

{descricao}

✅ *Não perca o prazo!*
📲 Apresente este documento no posto de saúde.

Para mais informações, procure a unidade de saúde mais próxima.

*NASST Digital - Saúde em primeiro lugar* 🏥
"""
    
    # Template para dose agendada
    TEMPLATE_DOSE = """
💉 *LEMBRETE DE VACINAÇÃO* 💉

Olá *{nome}*,

Sua próxima dose da vacina *{vacina}* está agendada para:

📅 *Data:* {data_agendamento}
📍 *Local:* {local}

🔔 *Não se esqueça de levar seu cartão de vacinação e documento de identificação.*

Em caso de dúvidas, entre em contato com a unidade de saúde.

*NASST Digital - Cuidando da sua saúde* 🏥
"""
    
    @staticmethod
    def gerar_link_whatsapp(telefone: str, mensagem: str) -> str:
        """
        Gera um link para abrir o WhatsApp com a mensagem pré-preenchida
        
        Args:
            telefone: Número de telefone (apenas números, com DDD)
            mensagem: Texto da mensagem
            
        Returns:
            URL para abrir no WhatsApp
        """
        # Limpar telefone (remover caracteres não numéricos)
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        
        # Adicionar código do país se não tiver
        if len(telefone_limpo) == 11:  # Já tem DDD + 9 dígitos
            telefone_formatado = f"55{telefone_limpo}"
        elif len(telefone_limpo) == 10:  # Tem DDD + 8 dígitos (telefone fixo)
            telefone_formatado = f"55{telefone_limpo}"
        else:
            telefone_formatado = telefone_limpo
        
        # Codificar a mensagem para URL
        mensagem_codificada = urllib.parse.quote(mensagem)
        
        # Gerar link
        link = f"https://wa.me/{telefone_formatado}?text={mensagem_codificada}"
        
        return link
    
    @staticmethod
    def formatar_telefone(telefone: str) -> str:
        """
        Formata um número de telefone para exibição
        """
        numeros = ''.join(filter(str.isdigit, telefone))
        if len(numeros) == 11:
            return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
        elif len(numeros) == 10:
            return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
        else:
            return telefone


class NotificacaoCampanhaService:
    """
    Serviço para gerenciar notificações de campanhas
    """
    
    def __init__(self, db):
        self.db = db
        self.whatsapp = WhatsAppService()
    
    def buscar_servidores_para_campanha(self, campanha_id: int) -> pd.DataFrame:
        """
        Busca servidores que se encaixam no público-alvo de uma campanha
        """
        # Buscar dados da campanha
        campanha = self.db.fetchone(
            "SELECT * FROM campanhas WHERE id = ?",
            (campanha_id,)
        )
        
        if not campanha:
            return pd.DataFrame()
        
        # Query base
        query = """
            SELECT 
                id_comp,
                nome,
                cpf,
                telefone,
                email,
                lotacao,
                superintendencia
            FROM servidores
            WHERE situacao_funcional = 'ATIVO'
              AND telefone IS NOT NULL 
              AND telefone != ''
              AND telefone != 'Nao informado'
        """
        
        servidores = self.db.read_sql(query)
        
        return servidores
    
    def buscar_servidores_com_doses_agendadas(self, dias_antecedencia: int = 7) -> pd.DataFrame:
        """
        Busca servidores com doses agendadas para os próximos dias
        """
        from datetime import date, timedelta
        
        hoje = date.today()
        data_fim = hoje + timedelta(days=dias_antecedencia)
        
        query = """
            SELECT 
                d.id as dose_id,
                d.id_comp,
                d.vacina,
                d.dose,
                d.data_ret as data_agendamento,
                d.local_aplicacao,
                s.nome,
                s.telefone,
                s.lotacao
            FROM doses d
            JOIN servidores s ON d.id_comp = s.id_comp
            WHERE d.data_ret BETWEEN ? AND ?
              AND s.telefone IS NOT NULL 
              AND s.telefone != ''
              AND s.telefone != 'Nao informado'
            ORDER BY d.data_ret
        """
        
        return self.db.read_sql(query, (hoje.isoformat(), data_fim.isoformat()))
    
    def gerar_mensagem_campanha(self, servidor: Dict, campanha: Dict) -> str:
        """
        Gera mensagem personalizada para uma campanha
        """
        from core.security import Formatters
        
        return WhatsAppService.TEMPLATE_CAMPANHA.format(
            nome=servidor['nome'].split()[0],  # Primeiro nome
            nome_campanha=campanha['nome_campanha'],
            vacina=campanha['vacina'],
            data_inicio=Formatters.formatar_data_br(campanha['data_inicio']),
            data_fim=Formatters.formatar_data_br(campanha['data_fim']),
            local="NASST Central",  # Pode ser personalizado
            publico_alvo=campanha['publico_alvo'] if campanha['publico_alvo'] else "Todos os servidores",
            descricao=campanha['descricao'] if campanha['descricao'] else "Participe da campanha de vacinação!"
        )
    
    def gerar_mensagem_dose_agendada(self, servidor: Dict, dose: Dict) -> str:
        """
        Gera mensagem para dose agendada
        """
        from core.security import Formatters
        
        return WhatsAppService.TEMPLATE_DOSE.format(
            nome=servidor['nome'].split()[0],
            vacina=dose['vacina'],
            data_agendamento=Formatters.formatar_data_br(dose['data_agendamento']),
            local=dose['local_aplicacao'] if dose['local_aplicacao'] else "NASST Central"
        )
    
    def gerar_links_lote(self, servidores: pd.DataFrame, mensagem_func) -> List[Dict]:
        """
        Gera links de WhatsApp para um lote de servidores
        """
        resultados = []
        
        for _, servidor in servidores.iterrows():
            telefone = servidor['telefone']
            if pd.notna(telefone) and telefone:
                mensagem = mensagem_func(servidor.to_dict())
                link = self.whatsapp.gerar_link_whatsapp(telefone, mensagem)
                
                resultados.append({
                    'id_comp': servidor['id_comp'],
                    'nome': servidor['nome'],
                    'telefone': self.whatsapp.formatar_telefone(telefone),
                    'link': link,
                    'mensagem': mensagem
                })
        
        return resultados