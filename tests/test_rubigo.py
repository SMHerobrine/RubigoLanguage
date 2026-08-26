from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from rubigo import RubigoError, compile_source
from rubigo.cli import main


class CompilerTests(unittest.TestCase):
    def test_transpiles_core_language(self) -> None:
        source = """\
function double(value: Integer):
    return Integer value * 2
end

function main():
    var change total: Integer = 0
    for number from 1 through 3:
        total = (total + double(number))
    end
    if total == 12 and true:
        print("total = {total}")
    else:
        print("wrong")
    end
end
"""
        rust = compile_source(source, "core.rb")

        self.assertIn("fn double(value: i64) -> i64", rust)
        self.assertIn("let mut total: i64 = 0;", rust)
        self.assertIn("for number in 1..=3", rust)
        self.assertIn("total = (total + double(number));", rust)
        self.assertIn("if (total == 12) && true", rust)
        self.assertIn('format!("total = {total}")', rust)
        self.assertIn("} else {", rust)

    def test_lists_builtins_and_raw_rust(self) -> None:
        source = """\
rust "use std::collections::HashMap;"

public function count(values: List(Integer)):
    rust "let _unused: Option<HashMap<i64, i64>> = None;"
    return Integer length(values)
end
"""
        rust = compile_source(source)

        self.assertIn("use std::collections::HashMap;", rust)
        self.assertIn("pub fn count(values: Vec<i64>) -> i64", rust)
        self.assertIn("(values.len() as i64)", rust)

    def test_comments_and_single_quoted_strings(self) -> None:
        source = """\
function main(): // comment
    # another comment
    print('hello')
end
"""
        rust = compile_source(source)
        self.assertIn('String::from("hello")', rust)

    def test_escaped_interpolation_braces_are_literal(self) -> None:
        source = """\
function main():
    var name = "Ada"
    print("Hello {name}; write \\{name\\} for a placeholder.")
    print("A literal \\{value\\}")
end
"""
        rust = compile_source(source)
        self.assertIn(
            'format!("Hello {name}; write {{name}} for a placeholder.")', rust
        )
        self.assertIn('String::from("A literal {value}")', rust)

    def test_diagnostic_includes_source_location(self) -> None:
        source = "function main():\n    var answer 42\nend\n"
        with self.assertRaises(RubigoError) as raised:
            compile_source(source, "broken.rb")

        rendered = raised.exception.render()
        self.assertIn("broken.rb:2:16", rendered)
        self.assertIn("expected '='", rendered)
        self.assertIn("^", rendered)

    def test_typed_returns_must_agree(self) -> None:
        source = """\
function choose(flag: Boolean):
    if flag:
        return String "yes"
    else:
        return Integer 0
    end
end
"""
        with self.assertRaises(RubigoError) as raised:
            compile_source(source, "returns.rb")

        self.assertIn("return type 'Integer' does not match 'String'", str(raised.exception))

    def test_cli_requires_rb_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.txt"
            source.write_text("function main():\nend\n", encoding="utf-8")
            errors = StringIO()
            with redirect_stderr(errors):
                result = main(["transpile", str(source)])

        self.assertEqual(result, 1)
        self.assertIn("Rubigo source files must use the .rb extension", errors.getvalue())

    def test_updated_examples_transpile(self) -> None:
        hello_source = Path("examples/hello.rb").read_text(encoding="utf-8")
        hello_rust = compile_source(hello_source, "examples/hello.rb")
        self.assertIn("fn greet(name: String) -> String", hello_rust)
        self.assertIn("let languages: Vec<String>", hello_rust)
        self.assertIn("let mut total: i64 = 0;", hello_rust)

        fizzbuzz_source = Path("examples/fizzbuzz.rb").read_text(encoding="utf-8")
        fizzbuzz_rust = compile_source(fizzbuzz_source, "examples/fizzbuzz.rb")
        self.assertIn("} else if (number % 3) == 0 {", fizzbuzz_rust)
        self.assertIn('println!("{}", number);', fizzbuzz_rust)

    def test_input_translation_matches_example(self) -> None:
        source_file = Path("examples/input.rb")
        rust = compile_source(source_file.read_text(encoding="utf-8"), str(source_file))
        expected = Path("examples/input.rs").read_text(encoding="utf-8")

        self.assertEqual(rust, expected)
        self.assertEqual(rust.count("fn __rubigo_input("), 1)
        self.assertIn("std::io::stdin()", rust)
        self.assertIn(".read_line(&mut value)", rust)
        self.assertIn("std::io::stdout().flush()", rust)

    def test_input_without_a_prompt(self) -> None:
        source = """\
function main():
    var value: String = input()
    print(value)
end
"""
        rust = compile_source(source, "promptless.rb")
        self.assertIn("__rubigo_input(String::new())", rust)

    def test_float_input_translation(self) -> None:
        source = """\
function main():
    var input_1: Float = input("Enter first Number")
    var input_2: Float = input("Enter second Number")
    print(input_1 + input_2)
end
"""
        rust = compile_source(source, "calc.rb")

        self.assertIn("let input_1: f64 = __rubigo_input", rust)
        self.assertIn('.parse::<f64>().expect("invalid numeric input")', rust)
        self.assertIn('println!("{}", (input_1 + input_2));', rust)

    def test_input_rejects_multiple_arguments(self) -> None:
        source = """\
function main():
    var value: String = input("first", "second")
end
"""
        with self.assertRaisesRegex(ValueError, "input expects zero or one argument"):
            compile_source(source, "invalid_input.rb")

    def test_guessing_game_syntax(self) -> None:
        source_file = Path("examples/guessing_game.rb")
        rust = compile_source(source_file.read_text(encoding="utf-8"), str(source_file))

        self.assertIn("let low_bound: i64 = __rubigo_input", rust)
        self.assertIn("let number = __rubigo_random_int(low_bound, high_bound);", rust)
        self.assertIn("let mut guess_counter: i64 = 0;", rust)
        self.assertIn("while guess_counter < chance {", rust)
        self.assertIn("guess_counter += 1;", rust)
        self.assertIn("} else if (guess_counter >= chance) && (guess != number) {", rust)
        self.assertEqual(rust.count("fn __rubigo_random_int("), 1)

    def test_random_int_rejects_wrong_argument_count(self) -> None:
        source = """\
function main():
    var number: random.int(10)
end
"""
        with self.assertRaisesRegex(ValueError, "random.int expects exactly two arguments"):
            compile_source(source, "invalid_random.rb")

    @unittest.skipUnless(shutil.which("rustc"), "rustc is not installed")
    def test_guessing_game_features_compile_as_rust(self) -> None:
        source = """\
function main():
    var number: random.int(1, 10)
    var change counter: Int = 0
    while counter < 1:
        counter += 1
        if number > 0:
            print(number)
        elif number == 0:
            print(counter)
end
"""
        rust = compile_source(source, "guessing_features.rb")

        with tempfile.TemporaryDirectory() as directory:
            rust_file = Path(directory) / "guessing_features.rs"
            output = Path(directory) / "guessing_features.rmeta"
            rust_file.write_text(rust, encoding="utf-8")
            result = subprocess.run(
                [
                    shutil.which("rustc"),
                    "--edition",
                    "2021",
                    "-D",
                    "warnings",
                    "--emit",
                    "metadata",
                    "-o",
                    str(output),
                    str(rust_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(shutil.which("rustc"), "rustc is not installed")
    def test_generated_examples_compile_as_rust(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for example_name in ("hello", "fizzbuzz", "input", "calc", "guessing_game"):
                source_file = Path("examples") / f"{example_name}.rb"
                rust = compile_source(source_file.read_text(encoding="utf-8"), str(source_file))
                rust_file = Path(directory) / f"{example_name}.rs"
                executable_suffix = ".exe" if shutil.which("where") else ""
                output = Path(directory) / f"{example_name}{executable_suffix}"
                rust_file.write_text(rust, encoding="utf-8")
                lint_arguments = (
                    ["-D", "warnings"] if example_name == "guessing_game" else []
                )
                result = subprocess.run(
                    [
                        "rustc",
                        "--edition",
                        "2021",
                        *lint_arguments,
                        str(rust_file),
                        "-o",
                        str(output),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
