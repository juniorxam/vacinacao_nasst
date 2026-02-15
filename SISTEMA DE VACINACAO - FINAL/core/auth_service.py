"""
auth_service.py - Serviços de autenticação e auditoria com rate limiting e bloqueio de conta
"""

import logging
from datetime import datetime
from typing import Dict, Optional

from .security import Security

logger = logging.getLogger(__name__)


class AuditLog:
    """Serviço de registro de logs de auditoria"""
    
    def __init__(self, db: "Database") -> None:
        self.db = db
        logger.debug("AuditLog inicializado")

    def registrar(self, usuario: str, modulo: str, acao: str, detalhes: str = "", ip_address: str = "127.0.0.1") -> None:
        """
        Registra uma ação no log de auditoria
        
        Args:
            usuario: Login do usuário que executou a ação
            modulo: Módulo do sistema (AUTH, SERVIDORES, etc)
            acao: Ação executada
            detalhes: Detalhes adicionais
            ip_address: Endereço IP do usuário
        """
        try:
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.db.execute(
                """
                INSERT INTO logs (data_hora, usuario, modulo, acao, detalhes, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (agora, usuario, modulo, acao, detalhes, ip_address),
            )
            logger.info(f"AUDIT: {usuario} - {modulo} - {acao} - {detalhes[:50]}")
        except Exception as e:
            logger.error(f"Erro ao registrar log de auditoria: {e}", exc_info=True)
            # Não relançar a exceção para não interromper o fluxo principal


class Auth:
    """Serviço de autenticação e autorização com rate limiting e bloqueio de conta"""
    
    def __init__(self, db: "Database") -> None:
        self.db = db
        self._login_attempts_memory = {}  # Rate limit em memória (por IP)
        logger.debug("Auth inicializado")

    def login(self, login: str, senha: str, ip: str = "127.0.0.1") -> Optional[Dict[str, str]]:
        """
        Realiza login do usuário com rate limiting e bloqueio de conta
        
        Args:
            login: Login do usuário
            senha: Senha do usuário
            ip: Endereço IP para rate limiting
            
        Returns:
            Dict com nome e nível de acesso ou None se falhar
        """
        # Rate limiting por IP (em memória)
        if not self._check_rate_limit_memory(ip):
            logger.warning(f"Rate limit excedido para IP {ip}")
            return None
        
        # Verificar bloqueio de conta (no banco)
        bloqueado, minutos = self._check_account_locked(login)
        if bloqueado:
            logger.warning(f"Conta {login} bloqueada por {minutos} minutos")
            return None

        try:
            senha_hash = Security.sha256_hex(senha)
            row = self.db.fetchone(
                "SELECT nome, nivel_acesso FROM usuarios WHERE login = ? AND senha = ? AND ativo = 1",
                (login, senha_hash),
            )
            
            if row:
                logger.info(f"Login bem-sucedido: {login} ({row['nivel_acesso']})")
                self._reset_rate_limit_memory(ip)
                # Limpar tentativas após login bem-sucedido
                self._clear_login_attempts(login)
                return {"nome": str(row["nome"]), "nivel_acesso": str(row["nivel_acesso"])}
            else:
                logger.warning(f"Tentativa de login falha: {login} (IP: {ip})")
                self._register_failed_attempt_memory(ip)
                # Registrar tentativa no banco
                self._register_failed_attempt_db(login, ip)
                return None
                
        except Exception as e:
            logger.error(f"Erro no login: {e}", exc_info=True)
            return None

    # ===== RATE LIMITING EM MEMÓRIA (POR IP) =====
    
    def _check_rate_limit_memory(self, ip: str) -> bool:
        """
        Verifica se o IP não excedeu o limite de tentativas (5 em 15 minutos)
        """
        if ip not in self._login_attempts_memory:
            return True
            
        attempts, first_attempt = self._login_attempts_memory[ip]
        
        # Reset após 15 minutos
        if (datetime.now() - first_attempt).seconds > 900:  # 15 minutos
            del self._login_attempts_memory[ip]
            return True
            
        # Máximo de 5 tentativas
        return attempts < 5

    def _register_failed_attempt_memory(self, ip: str):
        """Registra uma tentativa falha em memória"""
        now = datetime.now()
        if ip in self._login_attempts_memory:
            attempts, first = self._login_attempts_memory[ip]
            self._login_attempts_memory[ip] = (attempts + 1, first)
        else:
            self._login_attempts_memory[ip] = (1, now)

    def _reset_rate_limit_memory(self, ip: str):
        """Reseta o rate limit após login bem-sucedido"""
        if ip in self._login_attempts_memory:
            del self._login_attempts_memory[ip]

    # ===== BLOQUEIO DE CONTA (PERSISTENTE) =====
    
    def _check_account_locked(self, login: str) -> tuple[bool, int]:
        """
        Verifica se a conta está bloqueada por muitas tentativas (10 em 15 minutos)
        
        Returns:
            (bloqueado, minutos_restantes)
        """
        if not login:
            return False, 0
        
        # Buscar tentativas nos últimos 15 minutos
        tentativas = self.db.fetchall(
            """
            SELECT data_hora 
            FROM login_attempts 
            WHERE login = ? AND data_hora > datetime('now', '-15 minutes')
            ORDER BY data_hora
            """,
            (login,)
        )
        
        if len(tentativas) < 10:
            return False, 0
        
        # Calcular minutos restantes baseado na primeira tentativa
        primeira = datetime.fromisoformat(tentativas[0]['data_hora'].replace(' ', 'T'))
        agora = datetime.now()
        minutos_passados = (agora - primeira).seconds / 60
        minutos_restantes = max(0, 15 - minutos_passados)
        
        return True, int(minutos_restantes)

    def _register_failed_attempt_db(self, login: str, ip: str):
        """Registra tentativa falha no banco de dados"""
        try:
            self.db.execute(
                """
                INSERT INTO login_attempts (login, ip, data_hora) 
                VALUES (?, ?, datetime('now'))
                """,
                (login, ip)
            )
        except Exception as e:
            logger.error(f"Erro ao registrar tentativa no banco: {e}")

    def _clear_login_attempts(self, login: str):
        """Limpa tentativas de login após sucesso"""
        try:
            self.db.execute(
                "DELETE FROM login_attempts WHERE login = ?",
                (login,)
            )
        except Exception as e:
            logger.error(f"Erro ao limpar tentativas: {e}")

    # ===== PERMISSÕES =====

    @staticmethod
    def verificar_permissoes(user_level: str, needed_level: str) -> bool:
        """
        Verifica se o usuário tem permissão para acessar um recurso
        
        Args:
            user_level: Nível do usuário (ADMIN, OPERADOR, VISUALIZADOR)
            needed_level: Nível necessário para a ação
            
        Returns:
            True se tem permissão, False caso contrário
        """
        if user_level == "ADMIN":
            return True
        if user_level == "OPERADOR":
            return needed_level in ("OPERADOR", "VISUALIZADOR")
        if user_level == "VISUALIZADOR":
            return needed_level == "VISUALIZADOR"
        return False

    # ===== GERENCIAMENTO DE USUÁRIOS =====

    def criar_usuario(self, login: str, nome: str, senha: str, nivel: str, 
                      lotacao: str, ativo: bool = True, criado_por: str = None) -> tuple[bool, str]:
        """
        Cria um novo usuário no sistema
        
        Args:
            login: Login único do usuário
            nome: Nome completo
            senha: Senha (mínimo 6 caracteres)
            nivel: Nível de acesso
            lotacao: Lotação permitida
            ativo: Se o usuário está ativo
            criado_por: Login de quem está criando
            
        Returns:
            (sucesso, mensagem)
        """
        try:
            # Validações
            if len(senha) < 6:
                return False, "Senha deve ter pelo menos 6 caracteres"
                
            if not login or not login.strip():
                return False, "Login é obrigatório"
                
            if not nome or not nome.strip():
                return False, "Nome é obrigatório"
            
            # Verificar se login já existe
            existe = self.db.fetchone(
                "SELECT login FROM usuarios WHERE login = ?",
                (login.strip(),)
            )
            if existe:
                return False, f"Login '{login}' já existe"
            
            # Criar usuário
            senha_hash = Security.sha256_hex(senha)
            self.db.execute(
                """
                INSERT INTO usuarios (login, senha, nome, nivel_acesso, lotacao_permitida, ativo)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (login.strip(), senha_hash, nome.strip().upper(), nivel, lotacao, 1 if ativo else 0)
            )
            
            logger.info(f"Usuário criado: {login} por {criado_por}")
            return True, f"Usuário {login} criado com sucesso"
            
        except Exception as e:
            logger.error(f"Erro ao criar usuário {login}: {e}", exc_info=True)
            return False, f"Erro ao criar usuário: {str(e)}"

    def alterar_senha(self, login: str, senha_atual: str, nova_senha: str) -> tuple[bool, str]:
        """
        Altera a senha de um usuário
        
        Args:
            login: Login do usuário
            senha_atual: Senha atual para verificação
            nova_senha: Nova senha
            
        Returns:
            (sucesso, mensagem)
        """
        try:
            # Validações
            if len(nova_senha) < 6:
                return False, "Nova senha deve ter pelo menos 6 caracteres"
            
            # Verificar senha atual
            senha_atual_hash = Security.sha256_hex(senha_atual)
            usuario = self.db.fetchone(
                "SELECT login FROM usuarios WHERE login = ? AND senha = ? AND ativo = 1",
                (login, senha_atual_hash)
            )
            
            if not usuario:
                return False, "Senha atual incorreta"
            
            # Verificar se nova senha é diferente da atual
            if senha_atual == nova_senha:
                return False, "Nova senha deve ser diferente da atual"
            
            # Atualizar senha
            nova_senha_hash = Security.sha256_hex(nova_senha)
            self.db.execute(
                "UPDATE usuarios SET senha = ? WHERE login = ?",
                (nova_senha_hash, login)
            )
            
            logger.info(f"Senha alterada: {login}")
            return True, "Senha alterada com sucesso"
            
        except Exception as e:
            logger.error(f"Erro ao alterar senha {login}: {e}", exc_info=True)
            return False, f"Erro ao alterar senha: {str(e)}"

    def resetar_senha(self, login: str, nova_senha: str, admin_login: str) -> tuple[bool, str]:
        """
        Reseta a senha de um usuário (apenas admin)
        
        Args:
            login: Login do usuário
            nova_senha: Nova senha
            admin_login: Login do administrador
            
        Returns:
            (sucesso, mensagem)
        """
        try:
            if len(nova_senha) < 6:
                return False, "Nova senha deve ter pelo menos 6 caracteres"
            
            nova_senha_hash = Security.sha256_hex(nova_senha)
            self.db.execute(
                "UPDATE usuarios SET senha = ? WHERE login = ?",
                (nova_senha_hash, login)
            )
            
            logger.info(f"Senha resetada: {login} por admin {admin_login}")
            return True, f"Senha de {login} resetada com sucesso"
            
        except Exception as e:
            logger.error(f"Erro ao resetar senha {login}: {e}", exc_info=True)
            return False, f"Erro ao resetar senha: {str(e)}"

    def listar_usuarios(self, apenas_ativos: bool = True) -> list[Dict]:
        """
        Lista todos os usuários do sistema
        
        Args:
            apenas_ativos: Se True, lista apenas usuários ativos
            
        Returns:
            Lista de dicionários com dados dos usuários
        """
        try:
            query = "SELECT login, nome, nivel_acesso, lotacao_permitida, ativo, data_criacao FROM usuarios"
            if apenas_ativos:
                query += " WHERE ativo = 1"
            query += " ORDER BY nome"
            
            rows = self.db.fetchall(query)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Erro ao listar usuários: {e}", exc_info=True)
            return []