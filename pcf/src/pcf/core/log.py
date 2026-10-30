"""Logging that can't leak keys.

Every message, including exception tracebacks, passes through `MaskingFormatter`, which replaces
any known key value with ****. Actions logs on this repo are public (CONVENTIONS.md).
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterable

from pcf.config import get_config, secret_values

MASK = "****"
# Shorter values are too likely to match ordinary text, and too short to be a real key.
MIN_SECRET_LENGTH = 6


class MaskingFormatter(logging.Formatter):
    def __init__(self, secrets: Iterable[str], fmt: str | None = None) -> None:
        super().__init__(fmt)
        self.secrets = sorted(
            (s for s in secrets if len(s) >= MIN_SECRET_LENGTH), key=len, reverse=True
        )

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        for secret in self.secrets:
            text = text.replace(secret, MASK)
        return text


_configured = False


def setup_logging(level: str | None = None, secrets: Iterable[str] | None = None) -> None:
    """Send PCF's logs to stderr through the masking formatter. Safe to call more than once."""
    global _configured
    root = logging.getLogger("pcf")
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        MaskingFormatter(
            secret_values() if secrets is None else secrets,
            "%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    )
    root.addHandler(handler)
    root.setLevel(level or get_config().log_level)
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """A logger under `pcf.`, e.g. `get_logger(__name__)`."""
    if not _configured:
        setup_logging()
    return logging.getLogger(name if name.startswith("pcf") else f"pcf.{name}")
