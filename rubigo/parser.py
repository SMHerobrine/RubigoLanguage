from __future__ import annotations

from . import ast
from .errors import RubigoError
from .tokens import Token, TokenKind


BINARY_PRECEDENCE = {
    "or": 1,
    "||": 1,
    "and": 2,
    "&&": 2,
    "==": 3,
    "!=": 3,
    "<": 4,
    "<=": 4,
    ">": 4,
    ">=": 4,
    "+": 5,
    "-": 5,
    "*": 6,
    "/": 6,
    "%": 6,
}

COMPOUND_ASSIGNMENT_OPERATORS = {"+=", "-=", "*=", "/=", "%="}


class Parser:
    def __init__(self, tokens: list[Token], source: str, filename: str = "<input>") -> None:
        self.tokens = tokens
        self.source = source
        self.filename = filename
        self.index = 0

    def parse(self) -> ast.Program:
        functions: list[ast.Function] = []
        raw_items: list[ast.RawRust] = []
        self._skip_newlines()

        while not self._check_kind(TokenKind.EOF):
            public = self._match_word("public")
            if self._check_word("function"):
                functions.append(self._parse_function(public))
            elif self._check_word("rust") and not public:
                raw_items.append(self._parse_raw_rust())
            else:
                if public:
                    self._error(self._current, "expected 'function' after 'public'")
                self._error(self._current, "only functions and rust items are allowed at the top level")
            self._skip_newlines()

        return ast.Program(1, 1, functions, raw_items)

    def _parse_function(self, public: bool) -> ast.Function:
        keyword = self._expect_word("function")
        name = self._expect_kind(TokenKind.IDENTIFIER, "expected a function name")
        self._expect_symbol("(")
        parameters: list[ast.Parameter] = []
        if not self._check_symbol(")"):
            while True:
                mutable = self._match_word("mutable")
                parameter_name = self._expect_kind(TokenKind.IDENTIFIER, "expected a parameter name")
                self._expect_symbol(":")
                type_name = self._parse_type()
                parameters.append(
                    ast.Parameter(
                        parameter_name.line,
                        parameter_name.column,
                        parameter_name.value,
                        type_name,
                        mutable,
                    )
                )
                if not self._match_symbol(","):
                    break
        self._expect_symbol(")")

        declared_return_type = None
        if self._match_word("returns") or self._match_symbol("->"):
            declared_return_type = self._parse_type()
        self._expect_symbol(":")
        self._expect_line_end()

        body = self._parse_block({"end"}, keyword.column)
        self._expect_word("end")
        self._expect_line_end()
        return_type = self._resolve_return_type(declared_return_type, body)
        return ast.Function(
            keyword.line,
            keyword.column,
            name.value,
            parameters,
            return_type,
            body,
            public,
        )

    def _parse_type(self) -> ast.TypeName:
        name = self._expect_kind(TokenKind.IDENTIFIER, "expected a type name")
        arguments: list[ast.TypeName] = []
        closing_symbol = None
        if self._match_symbol("<"):
            closing_symbol = ">"
        elif self._match_symbol("("):
            closing_symbol = ")"

        if closing_symbol is not None:
            while True:
                arguments.append(self._parse_type())
                if not self._match_symbol(","):
                    break
            self._expect_symbol(closing_symbol)
        return ast.TypeName(name.line, name.column, name.value, arguments)

    def _parse_block(
        self,
        terminators: set[str],
        header_column: int | None = None,
    ) -> list[ast.Statement]:
        statements: list[ast.Statement] = []
        self._skip_newlines()
        indentation_delimited = (
            header_column is not None
            and not self._check_kind(TokenKind.EOF)
            and self._current.column > header_column
        )
        while not self._check_kind(TokenKind.EOF):
            if any(self._check_word(word) for word in terminators):
                break
            if indentation_delimited and self._current.column <= header_column:
                break
            statements.append(self._parse_statement())
            self._skip_newlines()
        if self._check_kind(TokenKind.EOF) and not indentation_delimited:
            expected = " or ".join(repr(word) for word in sorted(terminators))
            self._error(self._current, f"expected {expected} before the end of the file")
        return statements

    def _parse_statement(self) -> ast.Statement:
        if self._check_word("var"):
            return self._parse_var()
        if self._check_word("let"):
            return self._parse_legacy_let()
        if self._check_word("set"):
            return self._parse_assign()
        if self._check_word("print"):
            return self._parse_print()
        if self._check_word("if"):
            return self._parse_if()
        if self._check_word("while"):
            return self._parse_while()
        if self._check_word("for"):
            return self._parse_for()
        if self._check_word("return"):
            return self._parse_return()
        if self._check_word("break"):
            token = self._advance()
            self._expect_line_end()
            return ast.Break(token.line, token.column)
        if self._check_word("continue"):
            token = self._advance()
            self._expect_line_end()
            return ast.Continue(token.line, token.column)
        if self._check_word("rust"):
            return self._parse_raw_rust()

        expression = self._parse_expression()
        if self._match_symbol("="):
            value = self._parse_expression()
            self._expect_line_end()
            return ast.Assign(expression.line, expression.column, expression, value)
        if self._current.value in COMPOUND_ASSIGNMENT_OPERATORS:
            operator = self._advance()
            value = self._parse_expression()
            self._expect_line_end()
            return ast.CompoundAssign(
                expression.line,
                expression.column,
                expression,
                operator.value,
                value,
            )
        self._expect_line_end()
        return ast.ExpressionStatement(expression.line, expression.column, expression)

    def _parse_var(self) -> ast.Let:
        keyword = self._expect_word("var")
        mutable = self._match_word("change")
        name = self._expect_kind(TokenKind.IDENTIFIER, "expected a variable name")
        type_name = None
        value = None
        if self._match_symbol(":"):
            expression_start = self.index
            try:
                candidate_type = self._parse_type()
            except RubigoError:
                self.index = expression_start
            else:
                if self._match_symbol("="):
                    type_name = candidate_type
                else:
                    self.index = expression_start
            if type_name is None:
                value = self._parse_expression()
        elif not self._match_symbol("="):
            self._error(self._current, "expected '=' between the variable and its value")
        if value is None:
            value = self._parse_expression()
        self._expect_line_end()
        return ast.Let(keyword.line, keyword.column, name.value, value, type_name, mutable)

    def _parse_legacy_let(self) -> ast.Let:
        keyword = self._expect_word("let")
        mutable = self._match_word("mutable")
        name = self._expect_kind(TokenKind.IDENTIFIER, "expected a variable name")
        type_name = None
        if self._match_symbol(":"):
            type_name = self._parse_type()
        if not (self._match_word("be") or self._match_symbol("=")):
            self._error(self._current, "expected 'be' between the variable and its value")
        value = self._parse_expression()
        self._expect_line_end()
        return ast.Let(keyword.line, keyword.column, name.value, value, type_name, mutable)

    def _parse_assign(self) -> ast.Assign:
        keyword = self._expect_word("set")
        target = self._parse_expression()
        if not (self._match_word("to") or self._match_symbol("=")):
            self._error(self._current, "expected 'to' between the assignment target and value")
        value = self._parse_expression()
        self._expect_line_end()
        return ast.Assign(keyword.line, keyword.column, target, value)

    def _parse_print(self) -> ast.Print:
        keyword = self._expect_word("print")
        values: list[ast.Expression] = []

        parenthesized = self._match_symbol("(")
        if parenthesized:
            if not self._check_symbol(")"):
                values = self._parse_expression_list(")")
            self._expect_symbol(")")
        elif not self._at_line_end:
            values = self._parse_expression_list(None)

        self._expect_line_end()
        return ast.Print(keyword.line, keyword.column, values)

    def _parse_expression_list(self, closing_symbol: str | None) -> list[ast.Expression]:
        values = [self._parse_expression()]
        while self._match_symbol(","):
            if closing_symbol is not None and self._check_symbol(closing_symbol):
                break
            values.append(self._parse_expression())
        return values

    def _parse_if(self) -> ast.If:
        keyword = self._expect_word("if")
        condition = self._parse_expression()
        self._expect_symbol(":")
        self._expect_line_end()
        branches = [
            (
                condition,
                self._parse_block(
                    {"elif", "else", "otherwise", "end"},
                    keyword.column,
                ),
            )
        ]
        otherwise: list[ast.Statement] | None = None

        while (
            self._check_word("elif")
            or self._check_word("else")
            or self._check_word("otherwise")
        ):
            branch_word = self._advance()
            if branch_word.value == "elif" or self._match_word("if"):
                branch_condition = self._parse_expression()
                self._expect_symbol(":")
                self._expect_line_end()
                branches.append(
                    (
                        branch_condition,
                        self._parse_block(
                            {"elif", "else", "otherwise", "end"},
                            keyword.column,
                        ),
                    )
                )
                continue

            # Keep the established bare `else` spelling while also accepting
            # the colon used by indentation-oriented Rubigo code.
            self._match_symbol(":")
            self._expect_line_end()
            otherwise = self._parse_block({"end"}, keyword.column)
            if branch_word.value == "else" or branch_word.value == "otherwise":
                break

        self._finish_control_block(keyword)
        return ast.If(keyword.line, keyword.column, branches, otherwise)

    def _parse_while(self) -> ast.While:
        keyword = self._expect_word("while")
        condition = self._parse_expression()
        self._expect_symbol(":")
        self._expect_line_end()
        body = self._parse_block({"end"}, keyword.column)
        self._finish_control_block(keyword)
        return ast.While(keyword.line, keyword.column, condition, body)

    def _parse_for(self) -> ast.ForEach | ast.ForRange:
        keyword = self._expect_word("for")
        name = self._expect_kind(TokenKind.IDENTIFIER, "expected a loop variable")
        if self._match_word("in"):
            iterable = self._parse_expression()
            self._expect_symbol(":")
            self._expect_line_end()
            body = self._parse_block({"end"}, keyword.column)
            self._finish_control_block(keyword)
            return ast.ForEach(keyword.line, keyword.column, name.value, iterable, body)

        self._expect_word("from")
        start = self._parse_expression()
        if self._match_word("through"):
            inclusive = True
        else:
            self._expect_word("to")
            inclusive = False
        end = self._parse_expression()
        self._expect_symbol(":")
        self._expect_line_end()
        body = self._parse_block({"end"}, keyword.column)
        self._finish_control_block(keyword)
        return ast.ForRange(
            keyword.line,
            keyword.column,
            name.value,
            start,
            end,
            inclusive,
            body,
        )

    def _finish_control_block(self, keyword: Token) -> None:
        if self._check_word("end"):
            if self._current.column < keyword.column:
                return
            self._advance()
            self._expect_line_end()
            return

        if self._check_kind(TokenKind.EOF) or self._current.column <= keyword.column:
            return
        self._error(self._current, "expected 'end' or a dedented statement")

    def _parse_return(self) -> ast.Return:
        keyword = self._expect_word("return")
        type_name = self._parse_optional_return_type()
        value = None if self._at_line_end else self._parse_expression()
        self._expect_line_end()
        return ast.Return(keyword.line, keyword.column, value, type_name)

    def _parse_optional_return_type(self) -> ast.TypeName | None:
        if (
            self._current.kind != TokenKind.IDENTIFIER
            or not self._current.value[:1].isupper()
        ):
            return None

        start = self.index
        try:
            candidate = self._parse_type()
        except RubigoError:
            self.index = start
            return None
        if self._at_line_end:
            # `return Some(value)` and similar constructor calls are ordinary
            # expressions, not a typed return with a missing value.
            self.index = start
            return None
        return candidate

    def _resolve_return_type(
        self,
        declared: ast.TypeName | None,
        body: list[ast.Statement],
    ) -> ast.TypeName | None:
        annotated = list(self._typed_returns(body))
        resolved = declared or (annotated[0].type_name if annotated else None)
        if resolved is None:
            return None

        expected = self._type_signature(resolved)
        for statement in annotated:
            assert statement.type_name is not None
            actual = self._type_signature(statement.type_name)
            if actual != expected:
                raise RubigoError(
                    f"return type '{actual}' does not match '{expected}'",
                    statement.line,
                    statement.column,
                    filename=self.filename,
                    source=self.source,
                )
        return resolved

    def _typed_returns(self, statements: list[ast.Statement]):
        for statement in statements:
            if isinstance(statement, ast.Return) and statement.type_name is not None:
                yield statement
            elif isinstance(statement, ast.If):
                for _, branch in statement.branches:
                    yield from self._typed_returns(branch)
                if statement.otherwise is not None:
                    yield from self._typed_returns(statement.otherwise)
            elif isinstance(statement, (ast.While, ast.ForEach, ast.ForRange)):
                yield from self._typed_returns(statement.body)

    def _type_signature(self, type_name: ast.TypeName) -> str:
        if not type_name.arguments:
            return type_name.name
        arguments = ", ".join(self._type_signature(value) for value in type_name.arguments)
        return f"{type_name.name}({arguments})"

    def _parse_raw_rust(self) -> ast.RawRust:
        keyword = self._expect_word("rust")
        code = self._expect_kind(TokenKind.STRING, "expected Rust code in a quoted string")
        self._expect_line_end()
        return ast.RawRust(keyword.line, keyword.column, code.value)

    def _parse_expression(self, minimum_precedence: int = 0) -> ast.Expression:
        expression = self._parse_prefix()

        while True:
            if self._match_symbol("("):
                arguments: list[ast.Expression] = []
                if not self._check_symbol(")"):
                    arguments = self._parse_expression_list(")")
                self._expect_symbol(")")
                expression = ast.Call(expression.line, expression.column, expression, arguments)
                continue
            if self._match_symbol("["):
                index = self._parse_expression()
                self._expect_symbol("]")
                expression = ast.Index(expression.line, expression.column, expression, index)
                continue
            if self._match_symbol("."):
                name = self._expect_kind(TokenKind.IDENTIFIER, "expected a field or method name")
                expression = ast.Field(
                    expression.line,
                    expression.column,
                    expression,
                    name.value,
                )
                continue

            operator = self._current.value
            precedence = BINARY_PRECEDENCE.get(operator)
            if precedence is None or precedence < minimum_precedence:
                break
            self._advance()
            right = self._parse_expression(precedence + 1)
            expression = ast.Binary(
                expression.line,
                expression.column,
                expression,
                operator,
                right,
            )

        return expression

    def _parse_prefix(self) -> ast.Expression:
        token = self._current
        if token.value in {"-", "!", "not"}:
            self._advance()
            return ast.Unary(
                token.line,
                token.column,
                token.value,
                self._parse_expression(7),
            )

        if token.kind == TokenKind.INTEGER:
            self._advance()
            return ast.Literal(token.line, token.column, token.value, "integer")
        if token.kind == TokenKind.DECIMAL:
            self._advance()
            return ast.Literal(token.line, token.column, token.value, "decimal")
        if token.kind == TokenKind.STRING:
            self._advance()
            return ast.Literal(token.line, token.column, token.value, "string")
        if token.kind == TokenKind.IDENTIFIER and token.value in {"true", "false"}:
            self._advance()
            return ast.Literal(token.line, token.column, token.value == "true", "boolean")
        if token.kind == TokenKind.IDENTIFIER and token.value == "nothing":
            self._advance()
            return ast.Literal(token.line, token.column, None, "nothing")
        if token.kind == TokenKind.IDENTIFIER:
            self._advance()
            return ast.Name(token.line, token.column, token.value)
        if self._match_symbol("("):
            expression = self._parse_expression()
            self._expect_symbol(")")
            return expression
        if self._match_symbol("["):
            values: list[ast.Expression] = []
            if not self._check_symbol("]"):
                values = self._parse_expression_list("]")
            self._expect_symbol("]")
            return ast.ListLiteral(token.line, token.column, values)

        self._error(token, "expected an expression")

    @property
    def _current(self) -> Token:
        return self.tokens[self.index]

    @property
    def _at_line_end(self) -> bool:
        return self._check_kind(TokenKind.NEWLINE) or self._check_kind(TokenKind.EOF)

    def _advance(self) -> Token:
        token = self._current
        if not self._check_kind(TokenKind.EOF):
            self.index += 1
        return token

    def _skip_newlines(self) -> None:
        while self._check_kind(TokenKind.NEWLINE):
            self._advance()

    def _check_kind(self, kind: TokenKind) -> bool:
        return self._current.kind == kind

    def _check_word(self, value: str) -> bool:
        return self._current.kind == TokenKind.IDENTIFIER and self._current.value == value

    def _check_symbol(self, value: str) -> bool:
        return self._current.kind == TokenKind.SYMBOL and self._current.value == value

    def _match_word(self, value: str) -> bool:
        if not self._check_word(value):
            return False
        self._advance()
        return True

    def _match_symbol(self, value: str) -> bool:
        if not self._check_symbol(value):
            return False
        self._advance()
        return True

    def _expect_word(self, value: str) -> Token:
        if not self._check_word(value):
            self._error(self._current, f"expected '{value}'")
        return self._advance()

    def _expect_symbol(self, value: str) -> Token:
        if not self._check_symbol(value):
            self._error(self._current, f"expected '{value}'")
        return self._advance()

    def _expect_kind(self, kind: TokenKind, message: str) -> Token:
        if not self._check_kind(kind):
            self._error(self._current, message)
        return self._advance()

    def _expect_line_end(self) -> None:
        if self._check_kind(TokenKind.EOF):
            return
        if not self._check_kind(TokenKind.NEWLINE):
            self._error(self._current, "expected the end of the line")
        self._skip_newlines()

    def _error(self, token: Token, message: str) -> None:
        raise RubigoError(
            message,
            token.line,
            token.column,
            filename=self.filename,
            source=self.source,
        )


def parse(tokens: list[Token], source: str, filename: str = "<input>") -> ast.Program:
    return Parser(tokens, source, filename).parse()
