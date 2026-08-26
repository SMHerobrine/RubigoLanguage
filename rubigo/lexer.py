from __future__ import annotations

from .errors import RubigoError
from .tokens import ESCAPED_LEFT_BRACE, ESCAPED_RIGHT_BRACE, Token, TokenKind


TWO_CHARACTER_SYMBOLS = {
    "==",
    "!=",
    "<=",
    ">=",
    "&&",
    "||",
    "->",
    "..",
    "+=",
    "-=",
    "*=",
    "/=",
    "%=",
}
ONE_CHARACTER_SYMBOLS = set("()[]{}:,.+-*/%=<>!")


class Lexer:
    def __init__(self, source: str, filename: str = "<input>") -> None:
        self.source = source
        self.filename = filename
        self.index = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        while not self._at_end:
            character = self._peek()

            if character in " \t\r":
                self._advance()
            elif character == "\n":
                self.tokens.append(Token(TokenKind.NEWLINE, "\n", self.line, self.column))
                self._advance()
            elif character == "#":
                self._skip_comment()
            elif character == "/" and self._peek(1) == "/":
                self._skip_comment()
            elif character.isalpha() or character == "_":
                self._identifier()
            elif character.isdigit():
                self._number()
            elif character in {'"', "'"}:
                self._string()
            else:
                self._symbol()

        self.tokens.append(Token(TokenKind.EOF, "", self.line, self.column))
        return self.tokens

    @property
    def _at_end(self) -> bool:
        return self.index >= len(self.source)

    def _peek(self, distance: int = 0) -> str:
        position = self.index + distance
        return "\0" if position >= len(self.source) else self.source[position]

    def _advance(self) -> str:
        character = self.source[self.index]
        self.index += 1
        if character == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return character

    def _skip_comment(self) -> None:
        while not self._at_end and self._peek() != "\n":
            self._advance()

    def _identifier(self) -> None:
        line, column, start = self.line, self.column, self.index
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        self.tokens.append(
            Token(TokenKind.IDENTIFIER, self.source[start : self.index], line, column)
        )

    def _number(self) -> None:
        line, column, start = self.line, self.column, self.index
        while self._peek().isdigit() or self._peek() == "_":
            self._advance()

        kind = TokenKind.INTEGER
        if self._peek() == "." and self._peek(1).isdigit():
            kind = TokenKind.DECIMAL
            self._advance()
            while self._peek().isdigit() or self._peek() == "_":
                self._advance()

        self.tokens.append(Token(kind, self.source[start : self.index], line, column))

    def _string(self) -> None:
        quote = self._advance()
        line, column = self.line, self.column - 1
        characters: list[str] = []

        while not self._at_end and self._peek() != quote:
            if self._peek() == "\n":
                self._error("strings cannot span multiple lines", line, column)
            if self._peek() != "\\":
                characters.append(self._advance())
                continue

            self._advance()
            if self._at_end:
                self._error("unfinished escape sequence", self.line, self.column)
            escaped = self._advance()
            escapes = {
                "n": "\n",
                "r": "\r",
                "t": "\t",
                "0": "\0",
                "\\": "\\",
                "\"": "\"",
                "'": "'",
                "{": ESCAPED_LEFT_BRACE,
                "}": ESCAPED_RIGHT_BRACE,
            }
            if escaped not in escapes:
                self._error(f"unknown escape sequence \\{escaped}", self.line, self.column - 1)
            characters.append(escapes[escaped])

        if self._at_end:
            self._error("unterminated string", line, column)
        self._advance()
        self.tokens.append(Token(TokenKind.STRING, "".join(characters), line, column))

    def _symbol(self) -> None:
        line, column = self.line, self.column
        pair = self._peek() + self._peek(1)
        if pair in TWO_CHARACTER_SYMBOLS:
            self._advance()
            self._advance()
            self.tokens.append(Token(TokenKind.SYMBOL, pair, line, column))
            return

        character = self._peek()
        if character in ONE_CHARACTER_SYMBOLS:
            self._advance()
            self.tokens.append(Token(TokenKind.SYMBOL, character, line, column))
            return

        self._error(f"unexpected character {character!r}", line, column)

    def _error(self, message: str, line: int, column: int) -> None:
        raise RubigoError(
            message,
            line,
            column,
            filename=self.filename,
            source=self.source,
        )


def tokenize(source: str, filename: str = "<input>") -> list[Token]:
    return Lexer(source, filename).tokenize()
