from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


# Private marker characters preserve whether a source brace was escaped until
# code generation decides between an ordinary Rust string and format!.
ESCAPED_LEFT_BRACE = "\ue000"
ESCAPED_RIGHT_BRACE = "\ue001"


class TokenKind(Enum):
    IDENTIFIER = auto()
    INTEGER = auto()
    DECIMAL = auto()
    STRING = auto()
    SYMBOL = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass(frozen=True, slots=True)
class Token:
    kind: TokenKind
    value: str
    line: int
    column: int
