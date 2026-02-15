"""
test_security.py - Testes para o módulo de segurança
"""

import pytest
from core.security import Security, Formatters
from datetime import date, datetime


class TestSecurity:
    """Testes para a classe Security"""
    
    def test_sha256_hex(self):
        """Testa geração de hash SHA-256"""
        senha = "admin123"
        hash_result = Security.sha256_hex(senha)
        
        assert isinstance(hash_result, str)
        assert len(hash_result) == 64  # SHA-256 tem 64 caracteres hex
        assert hash_result == "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"  # Hash conhecido
    
    def test_clean_cpf(self):
        """Testa limpeza de CPF"""
        assert Security.clean_cpf("123.456.789-09") == "12345678909"
        assert Security.clean_cpf("12345678909") == "12345678909"
        assert Security.clean_cpf(None) == ""
        assert Security.clean_cpf(12345678909) == "12345678909"
    
    def test_validar_cpf_valido(self):
        """Testa validação de CPF válido"""
        assert Security.validar_cpf("12345678909") is True  # CPF válido conhecido
        assert Security.validar_cpf("529.982.247-25") is True  # CPF válido conhecido
    
    def test_validar_cpf_invalido(self):
        """Testa validação de CPF inválido"""
        assert Security.validar_cpf("11111111111") is False  # Todos dígitos iguais
        assert Security.validar_cpf("12345678900") is False  # Dígitos verificadores errados
        assert Security.validar_cpf("123") is False  # Tamanho errado
        assert Security.validar_cpf("") is False
    
    def test_formatar_cpf(self):
        """Testa formatação de CPF"""
        assert Security.formatar_cpf("12345678909") == "123.456.789-09"
        assert Security.formatar_cpf("123") == "123"  # Mantém como está se não tiver 11 dígitos
        assert Security.formatar_cpf(None) == ""
    
    def test_safe_select_only(self):
        """Testa validação de consultas SQL seguras"""
        # Consultas válidas
        valido, msg = Security.safe_select_only("SELECT * FROM servidores")
        assert valido is True
        
        valido, msg = Security.safe_select_only("SELECT nome, cpf FROM servidores WHERE id = 1")
        assert valido is True
        
        # Consultas inválidas - CORREÇÃO: Verificar mensagem em português
        valido, msg = Security.safe_select_only("INSERT INTO servidores VALUES (1)")
        assert valido is False
        assert "bloqueado" in msg.lower() or "apenas consultas select" in msg.lower()
        
        valido, msg = Security.safe_select_only("DROP TABLE servidores")
        assert valido is False
        
        valido, msg = Security.safe_select_only("DELETE FROM servidores")
        assert valido is False
        
        # Testar com comandos em maiúsculas
        valido, msg = Security.safe_select_only("INSERT INTO servidores")
        assert valido is False
        
        valido, msg = Security.safe_select_only("UPDATE servidores SET nome='teste'")
        assert valido is False


class TestFormatters:
    """Testes para a classe Formatters"""
    
    def test_parse_date(self):
        """Testa parsing de datas"""
        # String formato ISO
        dt = Formatters.parse_date("2024-03-15")
        assert dt == date(2024, 3, 15)
        
        # String formato BR
        dt = Formatters.parse_date("15/03/2024")
        assert dt == date(2024, 3, 15)
        
        # String com hora
        dt = Formatters.parse_date("2024-03-15 14:30:00")
        assert dt == date(2024, 3, 15)
        
        # Objeto date
        hoje = date.today()
        dt = Formatters.parse_date(hoje)
        assert dt == hoje
        
        # Objeto datetime
        agora = datetime.now()
        dt = Formatters.parse_date(agora)
        assert dt == agora.date()
        
        # Valores nulos
        assert Formatters.parse_date(None) is None
        assert Formatters.parse_date("") is None
        assert Formatters.parse_date("invalido") is None
    
    def test_formatar_data_br(self):
        """Testa formatação de data no padrão BR"""
        dt = date(2024, 3, 15)
        assert Formatters.formatar_data_br(dt) == "15/03/2024"
        
        assert Formatters.formatar_data_br("2024-03-15") == "15/03/2024"
        assert Formatters.formatar_data_br("") == ""
        assert Formatters.formatar_data_br(None) == ""
    
    def test_calcular_idade(self):
        """Testa cálculo de idade"""
        # Pessoa nascida em 15/03/1980
        nascimento = date(1980, 3, 15)
        idade = Formatters.calcular_idade(nascimento)
        
        # Idade depende da data atual, mas deve ser positiva
        assert idade is not None
        assert idade > 0
        
        # Nascimento inválido
        assert Formatters.calcular_idade(None) is None
        assert Formatters.calcular_idade("") is None
    
    def test_calcular_tempo_servico(self):
        """Testa cálculo de tempo de serviço"""
        # Admissão em 10/03/2010
        admissao = date(2010, 3, 10)
        tempo = Formatters.calcular_tempo_servico(admissao)
        
        assert isinstance(tempo, str)
        assert "ano" in tempo or "mes" in tempo
        
        # Admissão inválida
        assert Formatters.calcular_tempo_servico(None) == "Não informado"