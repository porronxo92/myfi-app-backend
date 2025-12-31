import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from typing import Optional

# Directorio de logs
LOGS_DIR = Path(r"C:\Users\rcruzd\OneDrive - Indra\Documentos\Workspace VS\AppFinanzas\logsBackend")

# Crear directorio si no existe
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Formato de logs con el nombre del fichero Python
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(filename)s | %(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Nombre del archivo de log único con fecha
def get_log_filename():
    """Genera el nombre del archivo de log con la fecha actual"""
    fecha = datetime.now().strftime("%Y%m%d")
    return LOGS_DIR / f"app_finance_{fecha}.log"


class ColoredFormatter(logging.Formatter):
    """Formatter con colores para consola"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        log_message = super().format(record)
        return f"{self.COLORS.get(record.levelname, '')}{log_message}{self.COLORS['RESET']}"


# Handler compartido para todos los loggers
_shared_file_handler = None
_shared_console_handler = None


def get_shared_file_handler():
    """Obtiene o crea el handler de archivo compartido"""
    global _shared_file_handler
    
    if _shared_file_handler is None:
        log_file = get_log_filename()
        
        # Handler con rotación diaria a medianoche
        _shared_file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=30,  # Mantener 30 días
            encoding='utf-8'
        )
        _shared_file_handler.setLevel(logging.DEBUG)
        _shared_file_handler.suffix = "%Y%m%d"
        
        # Formato del archivo
        file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        _shared_file_handler.setFormatter(file_formatter)
    
    return _shared_file_handler


def get_shared_console_handler(colored: bool = True):
    """Obtiene o crea el handler de consola compartido"""
    global _shared_console_handler
    
    if _shared_console_handler is None:
        _shared_console_handler = logging.StreamHandler(sys.stdout)
        _shared_console_handler.setLevel(logging.INFO)
        
        # Formato de consola
        if colored:
            console_formatter = ColoredFormatter(LOG_FORMAT, DATE_FORMAT)
        else:
            console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        
        _shared_console_handler.setFormatter(console_formatter)
    
    return _shared_console_handler


def setup_logger(
    name: str,
    level: int = logging.INFO,
    console_output: bool = True,
    colored_console: bool = True
) -> logging.Logger:
    """
    Configura un logger que escribe en el archivo único compartido.
    
    Args:
        name: Nombre del logger
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Si debe mostrar logs en consola
        colored_console: Si debe usar colores en consola
        
    Returns:
        logging.Logger: Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # CRÍTICO: Deshabilitar propagación para evitar duplicados
    logger.propagate = False
    
    # Evitar duplicar handlers si ya existe
    if logger.handlers:
        return logger
    
    # Agregar handler de archivo compartido
    logger.addHandler(get_shared_file_handler())
    
    # Agregar handler de consola si está habilitado
    if console_output:
        logger.addHandler(get_shared_console_handler(colored_console))
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Obtiene un logger configurado con el archivo único compartido.
    
    Args:
        name: Nombre del logger (ej: 'app.routes.upload', 'app.database')
        
    Returns:
        logging.Logger: Logger solicitado
    """
    logger = logging.getLogger(name)
    
    # Si no tiene handlers, configurarlo
    if not logger.handlers:
        setup_logger(name, level=logging.INFO)
    
    return logger


# Helper para logging de excepciones
def log_exception(logger: logging.Logger, exc: Exception, context: str = ""):
    """
    Registra una excepción con contexto completo.
    
    Args:
        logger: Logger a usar
        exc: Excepción capturada
        context: Contexto adicional
    """
    logger.error(
        f"Exception in {context}: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={"exception_type": type(exc).__name__}
    )


# Configurar loggers principales al importar el módulo
def setup_project_loggers():
    """Configura todos los loggers del proyecto para usar el archivo único"""
    
    # Logger principal de la aplicación
    app_logger = setup_logger("app", level=logging.INFO)
    
    # Logger de main
    main_logger = setup_logger("app.main", level=logging.INFO)
    
    # Logger de seguridad
    security_logger = setup_logger("app.security", level=logging.WARNING)
    
    # Logger de uploads
    upload_logger = setup_logger("app.upload", level=logging.INFO)
    
    # Logger de acceso HTTP
    access_logger = setup_logger("app.access", level=logging.INFO)
    
    # Logger de errores (mismo archivo, pero útil tenerlo separado lógicamente)
    error_logger = setup_logger("app.errors", level=logging.ERROR)
    
    return {
        "app": app_logger,
        "main": main_logger,
        "errors": error_logger,
        "access": access_logger,
        "security": security_logger,
        "upload": upload_logger
    }


# Inicializar loggers al importar el módulo
loggers = setup_project_loggers()

# Exportar loggers comunes
app_logger = loggers["app"]
error_logger = loggers["errors"]
access_logger = loggers["access"]
security_logger = loggers["security"]
upload_logger = loggers["upload"]
