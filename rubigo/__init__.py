"""Rubigo: a human-readable language that transpiles to Rust."""

from .compiler import compile_source
from .errors import RubigoError

__all__ = ["RubigoError", "compile_source"]
__version__ = "0.1.0"

