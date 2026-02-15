"""
logger.py - Configuração centralizada de logging
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import CONFIG


def setup_logging():
    """Configura o sistema de logging da aplicação"""
    
    # Criar diretório de logs se não existir
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Nome do arquivo de log com data
    log_file = log_dir / f"nasst_{datetime.now().strftime('%Y%m')}.log"
    
    # Formato do log
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configurar handler para arquivo (com rotação)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Configurar handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Configurar nível baseado no ambiente
    if CONFIG.environment == "production":
        level = logging.WARNING
        console_handler.setLevel(logging.WARNING)
    else:
        level = logging.DEBUG
        console_handler.setLevel(logging.DEBUG)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Silenciar logs muito verbosos de bibliotecas
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("pdfplumber").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name):
    """Obtém um logger configurado"""
    return logging.getLogger(name)