"""
test_database.py - Testes para o módulo de banco de dados
"""

import pytest
import sqlite3
from core.database import Database, OptimizedDatabase


class TestDatabase:
    """Testes para a classe Database"""
    
    def test_init(self, temp_db_path):
        """Testa inicialização do banco"""
        db = Database(temp_db_path)
        assert db.db_path == temp_db_path
    
    def test_init_schema(self, db):
        """Testa criação do schema"""
        # Verifica se as tabelas foram criadas
        tables = [
            "servidores",
            "estrutura_organizacional",
            "campanhas",
            "doses",
            "usuarios",
            "logs",
            "vacinas_cadastradas"
        ]
        
        for table in tables:
            result = db.fetchone(
                "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
                (table,)
            )
            assert result is not None, f"Tabela {table} não foi criada"
    
    def test_execute(self, db):
        """Testa execução de INSERT/UPDATE/DELETE"""
        # Inserir
        result = db.execute(
            "INSERT INTO vacinas_cadastradas (nome, fabricante, doses_necessarias) VALUES (?, ?, ?)",
            ("Vacina Teste", "Lab Teste", 2)
        )
        assert result == 1  # rowcount
        
        # Verificar inserção
        row = db.fetchone(
            "SELECT * FROM vacinas_cadastradas WHERE nome = ?",
            ("Vacina Teste",)
        )
        assert row is not None
        assert row["fabricante"] == "Lab Teste"
        
        # Atualizar
        result = db.execute(
            "UPDATE vacinas_cadastradas SET doses_necessarias = ? WHERE nome = ?",
            (3, "Vacina Teste")
        )
        assert result == 1
        
        # Verificar atualização
        row = db.fetchone(
            "SELECT doses_necessarias FROM vacinas_cadastradas WHERE nome = ?",
            ("Vacina Teste",)
        )
        assert row["doses_necessarias"] == 3
    
    def test_fetchone(self, db):
        """Testa busca de um registro"""
        # Inserir dados de teste
        db.execute(
            "INSERT INTO vacinas_cadastradas (nome, fabricante) VALUES (?, ?)",
            ("Teste Fetch", "Lab Teste")
        )
        
        # Buscar
        row = db.fetchone(
            "SELECT * FROM vacinas_cadastradas WHERE nome = ?",
            ("Teste Fetch",)
        )
        
        assert row is not None
        assert dict(row)["nome"] == "Teste Fetch"
        
        # Buscar inexistente
        row = db.fetchone(
            "SELECT * FROM vacinas_cadastradas WHERE nome = ?",
            ("Inexistente",)
        )
        assert row is None
    
    def test_fetchall(self, db):
        """Testa busca de múltiplos registros"""
        # Inserir dados de teste
        for i in range(3):
            db.execute(
                "INSERT INTO vacinas_cadastradas (nome, fabricante) VALUES (?, ?)",
                (f"Teste {i}", "Lab Teste")
            )
        
        # Buscar todos
        rows = db.fetchall(
            "SELECT * FROM vacinas_cadastradas WHERE fabricante = ? ORDER BY nome",
            ("Lab Teste",)
        )
        
        assert len(rows) >= 3
        assert isinstance(rows, list)
        assert all(isinstance(row, sqlite3.Row) for row in rows)
    
    def test_ensure_seed_data(self, db):
        """Testa criação de dados iniciais"""
        # Verifica se admin foi criado
        admin = db.fetchone(
            "SELECT * FROM usuarios WHERE login = ?",
            ("admin",)
        )
        assert admin is not None
        
        # Verifica se vacinas padrão foram criadas
        vacinas = db.fetchall("SELECT * FROM vacinas_cadastradas")
        assert len(vacinas) >= 8  # Pelo menos as 8 vacinas padrão


class TestOptimizedDatabase:
    """Testes para a classe OptimizedDatabase"""
    
    def test_cache(self, temp_db_path):
        """Testa funcionamento do cache"""
        db = OptimizedDatabase(temp_db_path)
        db.init_schema()
        
        # Primeira consulta (cache miss)
        df1 = db.read_sql("SELECT * FROM sqlite_master")
        
        # Segunda consulta (cache hit)
        df2 = db.read_sql("SELECT * FROM sqlite_master")
        
        stats = db.get_cache_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["cache_size"] > 0
    
    def test_cache_ttl(self, temp_db_path):
        """Testa expiração do cache por TTL"""
        import time
        db = OptimizedDatabase(temp_db_path)
        db.init_schema()
        
        # Primeira consulta com TTL curto
        db.read_sql("SELECT * FROM sqlite_master", ttl=1)
        
        # Espera o cache expirar
        time.sleep(1.1)
        
        # Segunda consulta (deve ser cache miss)
        db.read_sql("SELECT * FROM sqlite_master", ttl=1)
        
        stats = db.get_cache_stats()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 2