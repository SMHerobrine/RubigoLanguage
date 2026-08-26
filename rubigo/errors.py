from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SourceLocation:
    line: int
    column: int


class RubigoError(Exception):
    """An error that can be displayed against the original source."""

    def __init__(
        self,
        message: str,
        line: int,
        column: int,
        *,
        filename: str = "<input>",
        source: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column
        self.filename = filename
        self.source = source

    def render(self) -> str:
        heading = f"{self.filename}:{self.line}:{self.column}: error: {self.message}"
        if self.source is None:
            return heading

        lines = self.source.splitlines()
        if not 1 <= self.line <= len(lines):
            return heading

        source_line = lines[self.line - 1]
        gutter = str(self.line)
        caret_padding = " " * max(self.column - 1, 0)
        return "\n".join(
            (
                heading,
                f" {gutter} | {source_line}",
                f" {' ' * len(gutter)} | {caret_padding}^",
            )
        )

    def __str__(self) -> str:
        return self.render()

