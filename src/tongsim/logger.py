"""
logger.py

- Prefixed log format: `[TongSim_Lite][<module>] <message>`
- Supports per-module log level configuration
- Optional unified file logging
"""

import logging
from datetime import datetime
from pathlib import Path

__all__ = ["get_logger", "initialize_logger", "set_log_level"]


class _TongSimFormatter(logging.Formatter):
    """Log format: `[TongSim_Lite][<module>] <message>`."""

    def __init__(self, module_name: str):
        super().__init__()
        self.module_name = module_name

    def format(self, record: logging.LogRecord) -> str:
        try:
            msg = record.msg.format(*record.args)
        except Exception:
            msg = str(record.msg)
        record.getMessage = lambda: f"[TongSim_Lite][{self.module_name}] {msg}"
        return super().format(record)


class _LoggerManager:
    """Internal logger manager (module-private singleton)."""

    def __init__(self):
        self._default_level: int = logging.WARNING
        self._loggers: dict[str, logging.Logger] = {}
        self._file_handler: logging.Handler | None = None

    def configure(
        self,
        level: int = logging.INFO,
        log_to_file: bool = False,
        log_dir: str = "logs",
    ):
        """Configure the default log level and optional file logging."""

        # Configure logger levels
        self._default_level = level
        for module in self._loggers:
            self._loggers[module].setLevel(level)

        # Configure file logging
        if log_to_file and self._file_handler is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = Path(log_dir)
            path.mkdir(parents=True, exist_ok=True)
            file_path = path / f"TongSim_Lite-{timestamp}.log"
            handler = logging.FileHandler(file_path, encoding="utf-8")
            handler.setFormatter(
                logging.Formatter("[{asctime}] [{levelname}] {message}", style="{")
            )
            self._file_handler = handler
            for logger in self._loggers.values():
                logger.addHandler(handler)

    def get_logger(self, module_name: str) -> logging.Logger:
        """Get the logger instance for a given module name."""
        if module_name in self._loggers:
            return self._loggers[module_name]

        logger = logging.getLogger(f"TongSim_Lite.{module_name}")
        logger.propagate = False  # Loggers are hierarchical; do not propagate upward.
        logger.setLevel(self._default_level)

        # Console output
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(_TongSimFormatter(module_name))
        logger.addHandler(stream_handler)

        # File output
        if self._file_handler:
            logger.addHandler(self._file_handler)

        self._loggers[module_name] = logger
        return logger

    def set_module_level(self, module: str, level: int):
        """Set the log level for an existing module logger."""
        if module in self._loggers:
            self._loggers[module].setLevel(level)
        else:
            raise ValueError(f"Logger for module '{module}' has not been created yet.")


# Private singleton instance
_logger_manager = _LoggerManager()

# ===== Public API =====


def initialize_logger(
    level: int = logging.INFO, log_to_file: bool = False, log_dir: str = "logs"
):
    """
    Configure the default log level and file output options. Call once at program entry.

    :param level: Default log level (e.g. `logging.INFO`).
    :param log_to_file: Whether to write logs to a file.
    :param log_dir: Directory for log files (default: `logs/`).
    """
    _logger_manager.configure(level, log_to_file, log_dir)


def get_logger(module: str) -> logging.Logger:
    """
    Get a module logger. Prefix format: `[TongSim_Lite][<module>] <message>`.

    :param module: Module name.
    """
    return _logger_manager.get_logger(module)


def set_log_level(module: str, level: int):
    """
    Set the log level for a given module.

    :param module: Module name.
    :param level: Log level, e.g. `logging.DEBUG` or `logging.ERROR`.
    """
    _logger_manager.set_module_level(module, level)
