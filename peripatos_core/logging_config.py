"""Centralized logging setup for peripatos."""

import logging
import sys


def setup_logging() -> None:
    """Configure stdio logging. Always INFO level, output to stderr.

    Call once at CLI entry before any work. All existing module-level
    ``logger = logging.getLogger(__name__)`` calls produce output after this.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
