"""
database.py - Camada de persistência com logging, cache e otimizações
"""

import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from config import CONFIG

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database manager com WAL mode, retry logic e otimizações para concorrência
    """
    
    _MAX_WRITE_RETRIES = 6
    _BASE_BACKOFF_SEC = 0.08

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        logger.info(f"Inicializando banco de dados: {db_path}")

    @staticmethod
    def _is_busy_error(exc: Exception) -> bool:
        msg = str(exc).lower()
        return ("database is locked" in msg) or ("database is busy" in msg) or ("locked" in msg and "database" in msg)

    def _with_write_retry(self, fn):
        """Executa escrita com retry e backoff exponencial"""
        last_exc = None
        for attempt in range(self._MAX_WRITE_RETRIES):
            try:
                return fn()
            except sqlite3.OperationalError as e:
                last_exc = e
                if not self._is_busy_error(e):
                    logger.error(f"Erro não recuperável no banco: {e}")
                    raise
                wait_time = self._BASE_BACKOFF_SEC * (2 ** attempt)
                logger.warning(f"Banco ocupado, tentativa {attempt + 1}/{self._MAX_WRITE_RETRIES}. Aguardando {wait_time:.2f}s")
                time.sleep(wait_time)
        logger.error(f"Máximo de tentativas excedido: {last_exc}")
        raise last_exc

    @contextmanager
    def connect(self) -> Iterable[sqlite3.Connection]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            
            # Configurações otimizadas para 60 usuários simultâneos
            conn.execute("PRAGMA journal_mode=WAL;")           # Write-Ahead Logging para concorrência
            conn.execute("PRAGMA synchronous=NORMAL;")         # Equilíbrio entre segurança e performance
            conn.execute("PRAGMA foreign_keys=ON;")            # Integridade referencial
            conn.execute("PRAGMA temp_store=MEMORY;")          # Tabelas temporárias em memória
            conn.execute("PRAGMA busy_timeout=30000;")         # 30 segundos de timeout para locks
            
            # OTIMIZAÇÕES ADICIONAIS
            conn.execute("PRAGMA cache_size = -20000;")        # 20MB de cache
            conn.execute("PRAGMA mmap_size = 30000000;")       # 30MB memory mapping
            conn.execute("PRAGMA page_size = 4096;")           # Tamanho de página ideal
            conn.execute("PRAGMA threads = 4;")                # Usar 4 threads para queries
            
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Erro na conexão com banco: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close()

    def execute(self, query: str, params: Sequence[Any] = ()) -> int:
        def _run():
            with self.connect() as conn:
                cur = conn.execute(query, params)
                logger.debug(f"Execute: {query[:50]}... ({cur.rowcount} linhas)")
                return cur.rowcount
        return int(self._with_write_retry(_run))

    def executemany(self, query: str, params_seq: Sequence[Sequence[Any]]) -> int:
        if not params_seq:
            return 0
        def _run():
            with self.connect() as conn:
                cur = conn.executemany(query, params_seq)
                logger.debug(f"Executemany: {query[:50]}... ({len(params_seq)} lotes)")
                return cur.rowcount
        return int(self._with_write_retry(_run))

    def fetchone(self, query: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        with self.connect() as conn:
            cur = conn.execute(query, params)
            result = cur.fetchone()
            logger.debug(f"Fetchone: {query[:50]}... ({'encontrado' if result else 'não encontrado'})")
            return result

    def fetchall(self, query: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        with self.connect() as conn:
            cur = conn.execute(query, params)
            results = cur.fetchall()
            logger.debug(f"Fetchall: {query[:50]}... ({len(results)} registros)")
            return results

    def read_sql(self, query: str, params: Sequence[Any] = ()) -> pd.DataFrame:
        with self.connect() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            logger.debug(f"Read_sql: {query[:50]}... ({len(df)} registros)")
            return df

    def init_schema(self) -> None:
        """Inicializa o schema do banco de dados com TODOS os índices necessários"""
        logger.info("Inicializando schema do banco de dados")
        with self.connect() as conn:
            c = conn.cursor()
            
            # ===== TABELAS PRINCIPAIS =====
            
            # Tabela servidores
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS servidores (
                    id_comp TEXT PRIMARY KEY,
                    numfunc TEXT,
                    numvinc TEXT,
                    nome TEXT,
                    cpf TEXT,
                    data_nascimento DATE,
                    sexo TEXT,
                    cargo TEXT,
                    lotacao TEXT,
                    lotacao_fisica TEXT,
                    superintendencia TEXT,
                    telefone TEXT,
                    email TEXT,
                    data_admissao DATE,
                    tipo_vinculo TEXT,
                    situacao_funcional TEXT DEFAULT 'ATIVO',
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario_cadastro TEXT
                )
                """
            )
            
            # ÍNDICES PARA SERVIDORES
            c.execute("CREATE INDEX IF NOT EXISTS idx_servidores_cpf ON servidores(cpf)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_servidores_nome ON servidores(nome)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_servidores_superintendencia ON servidores(superintendencia)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_servidores_lotacao ON servidores(lotacao)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_servidores_situacao ON servidores(situacao_funcional)")
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_servidores_lotacao_situacao 
                ON servidores(lotacao, situacao_funcional)
            """)
            
            # Tabela estrutura organizacional
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS estrutura_organizacional (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setor TEXT NOT NULL,
                    superintendencia TEXT NOT NULL,
                    sigla_superintendencia TEXT,
                    local_fisico TEXT,
                    codigo TEXT,
                    ativo INTEGER DEFAULT 1,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_estrutura_setor ON estrutura_organizacional(setor)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_estrutura_superintendencia ON estrutura_organizacional(superintendencia)")

            # Tabela campanhas
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS campanhas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome_campanha TEXT UNIQUE,
                    vacina TEXT,
                    publico_alvo TEXT,
                    data_inicio DATE,
                    data_fim DATE,
                    status TEXT DEFAULT 'PLANEJADA',
                    descricao TEXT,
                    usuario_criacao TEXT,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Tabela doses (vacinações)
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS doses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_comp TEXT,
                    vacina TEXT,
                    tipo_vacina TEXT,
                    dose TEXT,
                    data_ap DATE,
                    data_ret DATE,
                    lote TEXT,
                    fabricante TEXT,
                    local_aplicacao TEXT,
                    via_aplicacao TEXT,
                    campanha_id INTEGER,
                    usuario_registro TEXT,
                    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_comp) REFERENCES servidores(id_comp),
                    FOREIGN KEY (campanha_id) REFERENCES campanhas(id)
                )
                """
            )
            
            # ÍNDICES PARA DOSES
            c.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_doses_unica_aplicacao
                ON doses (id_comp, vacina, dose, data_ap)
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_doses_id_comp ON doses(id_comp)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_doses_data_ap ON doses(data_ap)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_doses_campanha ON doses(campanha_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_doses_data_registro ON doses(data_registro)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_doses_usuario ON doses(usuario_registro)")

            # Tabela usuarios
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS usuarios (
                    login TEXT PRIMARY KEY,
                    senha TEXT,
                    nome TEXT,
                    nivel_acesso TEXT CHECK(nivel_acesso IN ('ADMIN', 'OPERADOR', 'VISUALIZADOR')),
                    lotacao_permitida TEXT,
                    ativo INTEGER DEFAULT 1,
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Tabela logs
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usuario TEXT,
                    modulo TEXT,
                    acao TEXT,
                    detalhes TEXT,
                    ip_address TEXT
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_logs_data_hora ON logs(data_hora)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs(usuario)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_logs_modulo ON logs(modulo)")

            # Tabela vacinas cadastradas
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS vacinas_cadastradas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE,
                    fabricante TEXT,
                    doses_necessarias INTEGER DEFAULT 1,
                    intervalo_dias INTEGER,
                    via_aplicacao TEXT,
                    contraindicacoes TEXT,
                    ativo INTEGER DEFAULT 1
                )
                """
            )
            
            # NOVA TABELA: tentativas de login (para bloqueio de conta)
            c.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT,
                    ip TEXT,
                    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_login_attempts_login ON login_attempts(login)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_login_attempts_data ON login_attempts(data_hora)")
            
            logger.info("Schema inicializado com sucesso")

    def ensure_seed_data(self) -> None:
        """Garante dados iniciais no banco"""
        logger.info("Verificando dados iniciais")
        from .security import Security
        
        # Só cria admin se estiver em desenvolvimento ou se a senha foi explicitamente fornecida
        admin_exists = self.fetchone("SELECT login FROM usuarios WHERE login = ?", (CONFIG.admin_login,))
        if not admin_exists and CONFIG.admin_password:
            senha_hash = Security.sha256_hex(CONFIG.admin_password)
            self.execute(
                """
                INSERT INTO usuarios (login, senha, nome, nivel_acesso, lotacao_permitida, ativo, data_criacao)
                VALUES (?, ?, ?, 'ADMIN', 'TODOS', 1, CURRENT_TIMESTAMP)
                """,
                (CONFIG.admin_login, senha_hash, "Administrador"),
            )
            logger.info(f"Usuário admin criado com login: {CONFIG.admin_login}")
        elif not admin_exists and CONFIG.environment == "production":
            logger.warning("Usuário admin não existe e senha não configurada. Criação manual necessária.")

        vacinas_padrao = [
            ("Hepatite B", "Butantan", 3, 30, "Intramuscular", "Hipersensibilidade"),
            ("Dupla Adulto (DT)", "Butantan", 1, 0, "Intramuscular", "Nenhuma"),
            ("Tríplice Viral", "Fiocruz", 1, 0, "Subcutânea", "Gestantes, imunossuprimidos"),
            ("Febre Amarela", "Bio-Manguinhos", 1, 0, "Subcutânea", "Alergia a ovo"),
            ("Influenza", "Vários", 1, 365, "Intramuscular", "Alergia a proteína do ovo"),
            ("COVID-19", "Vários", 2, 21, "Intramuscular", "Reação alérgica grave prévia"),
            ("Antirrábica", "Vários", 3, 7, "Intramuscular", "Nenhuma"),
            ("Meningocócica ACWY", "GSK", 1, 0, "Intramuscular", "Hipersensibilidade"),
        ]

        count = self.executemany(
            """
            INSERT OR IGNORE INTO vacinas_cadastradas
            (nome, fabricante, doses_necessarias, intervalo_dias, via_aplicacao, contraindicacoes, ativo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            vacinas_padrao,
        )
        logger.info(f"{count} vacinas padrão inseridas")

    def maybe_migrate_from_v6(self) -> None:
        """Migra dados da versão 6 se necessário"""
        if not os.path.exists(CONFIG.db_path_v6):
            return

        logger.info("Verificando migração do banco v6")
        v7_exists = os.path.exists(CONFIG.db_path_v7)
        if not v7_exists:
            self.init_schema()
            self.ensure_seed_data()
            self._migrate_tables_from_v6()
            return

        try:
            total_servidores = self.fetchone("SELECT COUNT(*) AS c FROM servidores")
            if total_servidores and int(total_servidores["c"]) > 0:
                logger.info("Banco v7 já contém dados, ignorando migração")
                return
        except Exception as e:
            logger.error(f"Erro ao verificar servidores: {e}")
            self.init_schema()
            self.ensure_seed_data()

        self._migrate_tables_from_v6()

    def _migrate_tables_from_v6(self) -> None:
        """Migra tabelas do banco v6"""
        logger.info("Iniciando migração do banco v6")
        try:
            with sqlite3.connect(CONFIG.db_path_v6, check_same_thread=False) as src:
                src.row_factory = sqlite3.Row

                def table_exists(conn: sqlite3.Connection, name: str) -> bool:
                    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (name,))
                    return cur.fetchone() is not None

                tables = ["servidores", "campanhas", "doses", "usuarios", "logs", "vacinas_cadastradas"]
                for t in tables:
                    if not table_exists(src, t):
                        logger.debug(f"Tabela {t} não existe no v6, ignorando")
                        continue

                    df = pd.read_sql_query(f"SELECT * FROM {t}", src)
                    if df.empty:
                        logger.debug(f"Tabela {t} vazia no v6")
                        continue

                    if t == "servidores":
                        if 'id_comp' not in df.columns:
                            df['id_comp'] = df['numfunc'].astype(str) + '-' + df['numvinc'].astype(str)
                        df = df.drop_duplicates(subset=['id_comp'], keep='first')

                    with self.connect() as dest:
                        dest_cols = [r["name"] for r in dest.execute(f"PRAGMA table_info({t})").fetchall()]
                        common = [c for c in df.columns if c in dest_cols]
                        if not common:
                            logger.warning(f"Nenhuma coluna em comum para tabela {t}")
                            continue

                        df2 = df[common].copy()
                        placeholders = ",".join(["?"] * len(common))
                        cols_clause = ",".join(common)
                        rows = [tuple(x) for x in df2.to_numpy()]

                        try:
                            dest.executemany(
                                f"INSERT OR IGNORE INTO {t} ({cols_clause}) VALUES ({placeholders})",
                                rows,
                            )
                            logger.info(f"Migrados {len(rows)} registros para {t}")
                        except sqlite3.IntegrityError as e:
                            if "UNIQUE constraint failed: servidores.cpf" in str(e):
                                for i, row in enumerate(rows):
                                    try:
                                        dest.execute(
                                            f"INSERT OR IGNORE INTO {t} ({cols_clause}) VALUES ({placeholders})",
                                            row,
                                        )
                                    except sqlite3.IntegrityError:
                                        logger.debug(f"Registro duplicado ignorado em {t}: {row[0] if row else 'N/A'}")
                                        continue
                            else:
                                logger.error(f"Erro ao migrar {t}: {e}")
                                raise
            logger.info("Migração do banco v6 concluída")
        except Exception as e:
            logger.error(f"Erro durante migração: {e}", exc_info=True)
            raise


class OptimizedDatabase(Database):
    """Database com cache de consultas"""
    
    def __init__(self, db_path: str) -> None:
        super().__init__(db_path)
        self._query_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("OptimizedDatabase inicializado com cache")
    
    def read_sql(self, query: str, params: Sequence[Any] = (), ttl: int = 60) -> pd.DataFrame:
        cache_key = f"{query}_{hash(str(params))}"
        
        if cache_key in self._query_cache:
            cached_time, data = self._query_cache[cache_key]
            if (datetime.now() - cached_time).seconds < ttl:
                self._cache_hits += 1
                logger.debug(f"Cache HIT: {query[:50]}...")
                return data.copy()
        
        self._cache_misses += 1
        logger.debug(f"Cache MISS: {query[:50]}...")
        
        with self._show_query_performance(query):
            result = super().read_sql(query, params)
        
        self._query_cache[cache_key] = (datetime.now(), result.copy())
        self._clean_old_cache(ttl)
        
        return result
    
    @contextmanager
    def _show_query_performance(self, query: str):
        start_time = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start_time
            if elapsed > 1.0:
                logger.warning(f"Query lenta ({elapsed:.2f}s): {query[:100]}...")
    
    def _clean_old_cache(self, ttl: int):
        current_time = datetime.now()
        to_remove = []
        
        for key, (cached_time, _) in self._query_cache.items():
            if (current_time - cached_time).seconds > ttl * 2:
                to_remove.append(key)
        
        for key in to_remove:
            del self._query_cache[key]
        
        if to_remove:
            logger.debug(f"Removidos {len(to_remove)} itens do cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0
        return {
            "cache_size": len(self._query_cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
        }
    
    def invalidate_cache_for_table(self, table_name: str):
        """
        Invalida todas as queries em cache que envolvem uma tabela específica
        """
        to_remove = []
        for key in list(self._query_cache.keys()):
            if table_name.lower() in key.lower():
                to_remove.append(key)
        
        for key in to_remove:
            del self._query_cache[key]
        
        if to_remove:
            logger.debug(f"Cache invalidado para tabela {table_name}: {len(to_remove)} queries")
    
    def execute(self, query: str, params: Sequence[Any] = ()) -> int:
        # Tentar identificar tabela afetada para invalidar cache
        palavras = query.lower().split()
        if any(p in palavras for p in ('update', 'insert', 'delete')):
            for i, palavra in enumerate(palavras):
                if palavra in ('update', 'insert', 'delete', 'into', 'from'):
                    if i + 1 < len(palavras):
                        tabela = palavras[i + 1].strip('(').strip(')')
                        self.invalidate_cache_for_table(tabela)
                        break
        
        return super().execute(query, params)
    
    def invalidate_cache(self, table_name: str = None):
        """Invalida o cache (total ou por tabela) - mantido para compatibilidade"""
        if table_name:
            self.invalidate_cache_for_table(table_name)
        else:
            self._query_cache.clear()
            logger.debug("Cache totalmente invalidado")