from __future__ import annotations

from .codegen import generate
from .lexer import tokenize
from .parser import parse


def compile_source(source: str, filename: str = "<input>") -> str:
    """Transpile Rubigo source text into Rust source text."""

    tokens = tokenize(source, filename)
    program = parse(tokens, source, filename)
    return generate(program)

