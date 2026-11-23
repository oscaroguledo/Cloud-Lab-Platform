"""Colored console logger: ``logger.info("request", method="GET", status=200)``.
Colors only on a terminal (``NO_COLOR``/``FORCE_COLOR``); ``exception=exc`` adds a traceback."""

import os
import sys
import traceback
from datetime import UTC, datetime
from typing import Any

# ANSI color codes
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_COLORS = {
    "DEBUG": "\033[36m",  # Cyan
    "INFO": "\033[32m",  # Green
    "WARNING": "\033[33m",  # Yellow
    "ERROR": "\033[31m",  # Red
    "CRITICAL": "\033[35m",  # Magenta
}


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return bool(os.environ.get("FORCE_COLOR")) or sys.stdout.isatty()


def _render_extras(kwargs: dict[str, Any]) -> str:
    extras = {k: v for k, v in kwargs.items() if k not in ("exception", "exc_info", "metadata")}
    extras.update(kwargs.get("metadata") or {})
    return "".join(f" {key}={value}" for key, value in extras.items())


def _print(level: str, name: str, message: str, kwargs: dict[str, Any]) -> None:
    ts = datetime.now(UTC).strftime("%H:%M:%SZ")  # UTC, so logs from any host line up
    text = message + _render_extras(kwargs)
    if _use_color():
        color = _COLORS.get(level, _RESET)
        line = f"{_DIM}{ts}{_RESET} {color}{_BOLD}{level:<8}{_RESET} {_DIM}[{name}]{_RESET} {text}"
    else:
        line = f"{ts} {level:<8} [{name}] {text}"
    print(line, flush=True)

    exc = kwargs.get("exception")
    if exc is None and kwargs.get("exc_info") is True:
        exc = sys.exc_info()[1]
    elif isinstance(kwargs.get("exc_info"), BaseException):
        exc = kwargs["exc_info"]
    if exc is not None:
        print("".join(traceback.format_exception(exc)), end="", flush=True)


class StructuredLogger:
    def __init__(self, name: str):
        self.name = name

    def _log(self, level: str, message: str, args: tuple, kwargs: dict) -> None:
        _print(level, self.name, message % args if args else message, kwargs)

    def debug(self, message: str, *args, **kwargs) -> None:
        self._log("DEBUG", message, args, kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        self._log("INFO", message, args, kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        self._log("WARNING", message, args, kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        self._log("ERROR", message, args, kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        self._log("CRITICAL", message, args, kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        self._log("ERROR", message, args, {**kwargs, "exc_info": kwargs.get("exc_info", True)})


def get_structured_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
