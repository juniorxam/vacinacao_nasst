"""
vacinacao_service.py - Serviço de vacinação
"""

import logging
import re
from datetime import date, timedelta
from typing import List, Optional, Tuple, Dict, Any

import pandas as pd
import pdfplumber
from dateutil.relativedelta import relativedelta

from core.auth_service import AuditLog

logger = logging.getLogger(__name__)


class VacinacaoService:
    """Serviço para gerenciamento de vacinações"""
    
    # Constantes para evitar strings mágicas
    LOCAL_PADRAO = "NASST Central"
    VIA_PADRAO = "Intramuscular"
    LOTE_NAO_INFORMADO = "NÃO INFORMADO"
    TIPO_CAMPANHA = "CAMPANHA"
    TIPO_ROTINA = "ROTINA"
    IMPORTADO_SUS = "Importado do Meu SUS"
    
    def __init__(self, db: "Database", audit: AuditLog) -> None:
        self.db = db
        self.audit = audit
        logger.debug("VacinacaoService inicializado")

    def listar_vacinas_ativas(self) -> List[str]:
        """Lista todas as vacinas ativas cadastradas"""
        try:
            df = self.db.read_sql("SELECT nome FROM vacinas_cadastradas WHERE ativo = 1 ORDER BY nome")
            if df.empty:
                return []
            return df["nome"].astype(str).tolist()
        except Exception as e:
            logger.error(f"Erro ao listar vacinas ativas: {e}", exc_info=True)
            return []

    def listar_campanhas_ativas(self) -> pd.DataFrame:
        """
        Lista campanhas ativas (status = 'ATIVA' e dentro do período)
        """
        try:
            hoje = date.today().isoformat()
            return self.db.read_sql(
                """
                SELECT id, nome_campanha, vacina, data_inicio, data_fim
                FROM campanhas 
                WHERE status = 'ATIVA' 
                  AND data_inicio <= ? 
                  AND data_fim >= ?
                ORDER BY data_inicio DESC
                """,
                (hoje, hoje)
            )
        except Exception as e:
            logger.error(f"Erro ao listar campanhas ativas: {e}", exc_info=True)
            return pd.DataFrame()
    
    def listar_todas_campanhas(self) -> pd.DataFrame:
        """
        Lista todas as campanhas (para seleção em registros)
        """
        try:
            return self.db.read_sql(
                """
                SELECT id, nome_campanha, vacina, status, data_inicio, data_fim
                FROM campanhas 
                ORDER BY data_inicio DESC
                """
            )
        except Exception as e:
            logger.error(f"Erro ao listar todas as campanhas: {e}", exc_info=True)
            return pd.DataFrame()

    def historico_servidor(self, id_comp: str) -> pd.DataFrame:
        """Retorna o histórico de vacinação de um servidor"""
        try:
            return self.db.read_sql(
                """
                SELECT d.*, c.nome_campanha
                FROM doses d
                LEFT JOIN campanhas c ON d.campanha_id = c.id
                WHERE d.id_comp = ?
                ORDER BY d.data_ap DESC
                """,
                (id_comp,),
            )
        except Exception as e:
            logger.error(f"Erro ao buscar histórico do servidor {id_comp}: {e}", exc_info=True)
            return pd.DataFrame()

    def _calcular_data_retorno(self, vacina: str, data_ap: date) -> date:
        """
        Calcula a data de retorno baseada no tipo de vacina
        
        Args:
            vacina: Nome da vacina
            data_ap: Data da aplicação
            
        Returns:
            Data de retorno calculada
        """
        vacina_lower = vacina.lower()
        
        if "influenza" in vacina_lower:
            return data_ap + relativedelta(years=1)
        elif "covid" in vacina_lower:
            return data_ap + timedelta(days=21)
        elif "hepatite" in vacina_lower:
            return data_ap + timedelta(days=30)
        else:
            return data_ap + timedelta(days=30)

    def registrar_dose(
        self,
        id_comp: str,
        vacina: str,
        dose: str,
        data_ap: date,
        data_ret: Optional[date] = None,
        lote: Optional[str] = None,
        fabricante: Optional[str] = None,
        local_aplicacao: str = LOCAL_PADRAO,
        via_aplicacao: str = VIA_PADRAO,
        campanha_id: Optional[int] = None,
        usuario: str = "",
    ) -> bool:
        """
        Registra uma dose de vacina para um servidor
        
        Returns:
            True se registrou, False se já existia ou erro
        """
        try:
            # Normalizar dados
            lote_final = (lote or "").strip() or self.LOTE_NAO_INFORMADO
            fabricante_final = (fabricante or "").strip() or "NAO INFORMADO"
            tipo_vacina = self.TIPO_CAMPANHA if campanha_id else self.TIPO_ROTINA
            
            # Calcular data de retorno se não fornecida
            if data_ret is None:
                data_ret = self._calcular_data_retorno(vacina, data_ap)

            # Verificar duplicata
            existe = self.db.fetchone(
                """
                SELECT id FROM doses 
                WHERE id_comp = ? AND vacina = ? AND dose = ? AND data_ap = ?
                """,
                (id_comp, vacina, dose, data_ap.isoformat())
            )
            
            if existe:
                logger.info(f"Registro duplicado ignorado: {id_comp} - {vacina} - {dose} - {data_ap}")
                return False

            # Inserir registro
            self.db.execute(
                """
                INSERT INTO doses
                (id_comp, vacina, tipo_vacina, dose, data_ap, data_ret, lote,
                 fabricante, local_aplicacao, via_aplicacao, campanha_id, usuario_registro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    id_comp,
                    vacina,
                    tipo_vacina,
                    dose,
                    data_ap.isoformat(),
                    data_ret.isoformat() if data_ret else None,
                    lote_final,
                    fabricante_final,
                    local_aplicacao,
                    via_aplicacao,
                    campanha_id,
                    usuario,
                ),
            )
            
            logger.info(f"Dose registrada: {id_comp} - {vacina} - {dose} por {usuario}")
            self.audit.registrar(
                usuario, 
                "VACINACAO", 
                "Registrou aplicacao de vacina", 
                f"{vacina} - {dose} ({id_comp})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Erro ao registrar dose para {id_comp}: {e}", exc_info=True)
            # Se for erro de unique constraint, retorna False
            if "UNIQUE constraint failed" in str(e):
                logger.info(f"Registro duplicado (constraint): {id_comp}")
                return False
            raise  # Outros erros são propagados

    def excluir_registro_vacina(self, dose_id: int, usuario: str, motivo: str = "") -> Tuple[bool, str]:
        """
        Exclui um registro de vacinação
        
        Args:
            dose_id: ID do registro de dose
            usuario: Login do usuário que está excluindo
            motivo: Motivo da exclusão (opcional)
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            # Verificar se a dose existe
            dose = self.db.fetchone(
                """
                SELECT d.id, d.id_comp, d.vacina, d.dose, d.data_ap, d.usuario_registro,
                       s.nome as servidor_nome
                FROM doses d
                LEFT JOIN servidores s ON d.id_comp = s.id_comp
                WHERE d.id = ?
                """,
                (dose_id,)
            )
            
            if not dose:
                logger.warning(f"Tentativa de excluir registro inexistente ID {dose_id}")
                return False, f"Registro de vacinação ID {dose_id} não encontrado."
            
            # Verificar permissão
            row = self.db.fetchone(
                "SELECT nivel_acesso FROM usuarios WHERE login = ?",
                (usuario,)
            )
            
            is_admin = row and row['nivel_acesso'] == 'ADMIN'
            
            if not is_admin and dose['usuario_registro'] and dose['usuario_registro'] != usuario:
                logger.warning(f"Usuário {usuario} tentou excluir registro de {dose['usuario_registro']}")
                return False, "Apenas administradores podem excluir registros de outros usuários."
            
            # Excluir o registro
            with self.db.connect() as conn:
                cursor = conn.execute("DELETE FROM doses WHERE id = ?", (dose_id,))
                rows_affected = cursor.rowcount
            
            if rows_affected == 0:
                return False, f"Nenhum registro encontrado com ID {dose_id}."
            
            # Registrar no log
            servidor_info = f" | Servidor: {dose['servidor_nome']}" if dose['servidor_nome'] else ""
            detalhes = f"ID: {dose_id} | Vacina: {dose['vacina']} | Dose: {dose['dose']} | Data: {dose['data_ap']}{servidor_info}"
            if motivo:
                detalhes += f" | Motivo: {motivo}"
                
            self.audit.registrar(usuario, "VACINACAO", "Excluiu registro de vacinação", detalhes)
            logger.info(f"Registro {dose_id} excluído por {usuario}")
            
            return True, f"Registro de vacinação ID {dose_id} excluído com sucesso!"
            
        except Exception as e:
            logger.error(f"Erro ao excluir registro {dose_id}: {e}", exc_info=True)
            return False, f"Erro ao excluir registro: {str(e)}"
    
    def listar_registros_por_periodo(self, data_inicio: date, data_fim: date, 
                                      usuario: Optional[str] = None) -> pd.DataFrame:
        """
        Lista registros de vacinação em um período
        
        Args:
            data_inicio: Data inicial
            data_fim: Data final
            usuario: Filtrar por usuário (opcional)
            
        Returns:
            DataFrame com os registros
        """
        try:
            query = """
                SELECT 
                    d.id,
                    d.data_ap,
                    d.vacina,
                    d.dose,
                    s.nome as servidor_nome,
                    s.cpf,
                    s.lotacao,
                    s.superintendencia,
                    d.usuario_registro,
                    d.data_registro
                FROM doses d
                JOIN servidores s ON d.id_comp = s.id_comp
                WHERE date(d.data_ap) BETWEEN ? AND ?
            """
            params = [data_inicio.isoformat(), data_fim.isoformat()]
            
            if usuario:
                query += " AND d.usuario_registro = ?"
                params.append(usuario)
            
            query += " ORDER BY d.data_ap DESC"
            
            return self.db.read_sql(query, params)
            
        except Exception as e:
            logger.error(f"Erro ao listar registros por período: {e}", exc_info=True)
            return pd.DataFrame()

    def registrar_em_lote(self, registros: List[Dict], usuario: str) -> Tuple[int, int, List[str]]:
        """
        Registra múltiplas vacinações em lote
        
        Args:
            registros: Lista de dicionários com dados das vacinações
            usuario: Usuário que está registrando
            
        Returns:
            (sucessos, duplicados, erros)
        """
        sucessos = 0
        duplicados = 0
        erros = []
        
        for i, registro in enumerate(registros):
            try:
                # Validar dados mínimos
                if not registro.get('id_comp'):
                    erros.append(f"Registro {i+1}: ID do servidor não informado")
                    continue
                    
                if not registro.get('vacina'):
                    erros.append(f"Registro {i+1}: Vacina não informada")
                    continue
                
                # Registrar
                sucesso = self.registrar_dose(
                    id_comp=registro['id_comp'],
                    vacina=registro['vacina'],
                    dose=registro.get('dose', '1ª Dose'),
                    data_ap=registro.get('data_ap', date.today()),
                    data_ret=registro.get('data_ret'),
                    lote=registro.get('lote'),
                    fabricante=registro.get('fabricante'),
                    local_aplicacao=registro.get('local_aplicacao', self.LOCAL_PADRAO),
                    via_aplicacao=registro.get('via_aplicacao', self.VIA_PADRAO),
                    campanha_id=registro.get('campanha_id'),
                    usuario=usuario
                )
                
                if sucesso:
                    sucessos += 1
                else:
                    duplicados += 1
                    
            except Exception as e:
                logger.error(f"Erro no registro em lote {i+1}: {e}")
                erros.append(f"Registro {i+1}: {str(e)}")
        
        logger.info(f"Registro em lote: {sucessos} sucessos, {duplicados} duplicados, {len(erros)} erros")
        return sucessos, duplicados, erros

    # ===== MÉTODOS PARA IMPORTAR PDF DA CARTEIRA NACIONAL DE VACINAÇÃO DIGITAL =====

    def extrair_dados_titular_pdf(self, arquivo_pdf) -> Dict[str, str]:
        """
        Extrai nome, CPF e data de nascimento do PDF da Carteira Nacional de Vacinação Digital.
        Retorna um dicionário com as chaves: 'nome', 'cpf', 'data_nascimento'.
        """
        dados = {'nome': None, 'cpf': None, 'data_nascimento': None}
        
        try:
            with pdfplumber.open(arquivo_pdf) as pdf:
                if not pdf.pages:
                    logger.warning("PDF sem páginas")
                    return dados
                    
                primeira_pagina = pdf.pages[0].extract_text()
            
            # Procurar CPF (formato 000.000.000-00)
            cpf_match = re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', primeira_pagina)
            if cpf_match:
                dados['cpf'] = cpf_match.group()
            
            # Procurar nome (após "Nome" na tabela de identificação)
            nome_match = re.search(r'Nome\s+([A-ZÀ-Ú\s]+?)\s+\d{2}/\d{2}/\d{4}', primeira_pagina)
            if nome_match:
                dados['nome'] = nome_match.group(1).strip()
            
            # Procurar data de nascimento (formato DD/MM/AAAA)
            nascimento_match = re.search(r'(\d{2}/\d{2}/\d{4})', primeira_pagina)
            if nascimento_match:
                dados['data_nascimento'] = nascimento_match.group(1)
            
            logger.info(f"Dados extraídos do PDF: Nome={dados['nome']}, CPF={dados['cpf']}")
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados do titular do PDF: {e}", exc_info=True)
        
        return dados

    def extrair_vacinas_pdf(self, arquivo_pdf) -> List[Dict[str, Any]]:
        """
        Extrai os registros de vacinação do PDF da Carteira Nacional de Vacinação Digital.
        Função específica para o formato do PDF do Meu SUS Digital.
        """
        vacinas = []
        vacinas_set = set()
        
        try:
            with pdfplumber.open(arquivo_pdf) as pdf:
                texto_completo = ""
                for pagina in pdf.pages:
                    texto_completo += pagina.extract_text() + "\n"
            
            # Dividir o texto em linhas
            linhas = texto_completo.split('\n')
            
            # Modo de extração: procurar por padrões específicos
            i = 0
            while i < len(linhas):
                linha = linhas[i].strip()
                
                # Procurar por linhas que começam com "COVID-19" ou "VACINA"
                if linha.startswith(('COVID-19', 'VACINA')):
                    # Esta linha contém uma vacina
                    vacina_completa = linha
                    
                    # Verificar se a próxima linha também faz parte
                    if i + 1 < len(linhas) and not linhas[i+1].strip().startswith(('COVID-19', 'VACINA')):
                        if re.search(r'\d{2}/\d{2}/\d{4}', linhas[i+1]):
                            vacina_completa += " " + linhas[i+1].strip()
                            i += 1
                    
                    # Extrair dados desta vacina
                    dados_vacina = self._extrair_dados_linha_vacina(vacina_completa)
                    if dados_vacina:
                        chave = f"{dados_vacina['vacina']}_{dados_vacina['data']}_{dados_vacina['dose']}"
                        if chave not in vacinas_set:
                            vacinas_set.add(chave)
                            vacinas.append(dados_vacina)
                
                i += 1
            
            logger.info(f"{len(vacinas)} vacinas extraídas do PDF")
            
        except Exception as e:
            logger.error(f"Erro ao extrair vacinas do PDF: {e}", exc_info=True)
        
        return vacinas
    
    def _extrair_dados_linha_vacina(self, linha: str) -> Optional[Dict[str, Any]]:
        """
        Extrai os dados de uma linha que contém uma vacina.
        """
        try:
            # Procurar por todas as datas na linha
            datas = re.findall(r'(\d{2}/\d{2}/\d{4})', linha)
            if not datas:
                return None
            
            # A primeira data é a data de aplicação
            data_ap = datas[0]
            
            # Encontrar a posição da data
            pos_data = linha.find(data_ap)
            
            # Tudo antes da data é o nome da vacina
            vacina = linha[:pos_data].strip()
            
            # Tudo depois são os outros campos
            resto = linha[pos_data + len(data_ap):].strip()
            partes = resto.split()
            
            # A dose é o primeiro campo após a data
            dose = partes[0] if partes else ""
            
            # O lote é o segundo campo
            lote = partes[1] if len(partes) > 1 else ""
            
            # Limpar o nome da vacina
            vacina = re.sub(r'\s+', ' ', vacina).strip()
            
            # Mapear doses abreviadas para o formato completo
            mapa_doses = {
                '1/2': '1ª Dose',
                '2/2': '2ª Dose',
                '1ª': '1ª Dose',
                '2ª': '2ª Dose',
                '3ª': '3ª Dose',
                'Única': 'Dose Única',
                'Reforço': 'Reforço'
            }
            
            for abrev, completo in mapa_doses.items():
                if abrev in dose:
                    dose = completo
                    break
            
            return {
                'vacina': vacina,
                'data': data_ap,
                'dose': dose,
                'lote': lote,
                'estrategia': '',
                'cnes': '',
                'estabelecimento': '',
                'municipio': '',
                'uf': ''
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados da linha de vacina: {e}")
            return None