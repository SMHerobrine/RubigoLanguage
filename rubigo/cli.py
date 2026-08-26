from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .compiler import compile_source
from .errors import RubigoError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rubigo",
        description="Transpile human-readable Rubigo programs to Rust.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    transpile = subparsers.add_parser("transpile", help="write Rust source")
    transpile.add_argument("source", type=Path, help="the .rb source file")
    transpile.add_argument("-o", "--output", type=Path, help="output .rs file")

    check = subparsers.add_parser("check", help="transpile and ask rustc to type-check")
    check.add_argument("source", type=Path, help="the .rb source file")

    run = subparsers.add_parser("run", help="transpile, compile, and run a program")
    run.add_argument("source", type=Path, help="the .rb source file")
    run.add_argument("program_arguments", nargs=argparse.REMAINDER)
    return parser


def _read_and_compile(path: Path) -> str:
    if path.suffix.lower() != ".rb":
        raise ValueError(f"Rubigo source files must use the .rb extension: {path}")
    source = path.read_text(encoding="utf-8")
    return compile_source(source, str(path))


def _require_rustc() -> str:
    rustc = shutil.which("rustc")
    if rustc is None:
        raise RuntimeError("rustc was not found; install Rust from https://rustup.rs")
    return rustc


def _transpile(source: Path, output: Path | None) -> int:
    rust = _read_and_compile(source)
    destination = output or source.with_suffix(".rs")
    destination.write_text(rust, encoding="utf-8")
    print(f"Wrote {destination}")
    return 0


def _check(source: Path) -> int:
    rustc = _require_rustc()
    rust = _read_and_compile(source)
    with tempfile.TemporaryDirectory(prefix="rubigo-") as directory:
        rust_file = Path(directory) / "program.rs"
        output_file = Path(directory) / "program.rmeta"
        rust_file.write_text(rust, encoding="utf-8")
        result = subprocess.run(
            [rustc, "--edition", "2021", "--emit", "metadata", "-o", str(output_file), str(rust_file)],
            check=False,
        )
    return result.returncode


def _run(source: Path, arguments: list[str]) -> int:
    rustc = _require_rustc()
    rust = _read_and_compile(source)
    with tempfile.TemporaryDirectory(prefix="rubigo-") as directory:
        rust_file = Path(directory) / "program.rs"
        executable = Path(directory) / ("program.exe" if sys.platform == "win32" else "program")
        rust_file.write_text(rust, encoding="utf-8")
        compile_result = subprocess.run(
            [rustc, "--edition", "2021", "-o", str(executable), str(rust_file)],
            check=False,
        )
        if compile_result.returncode != 0:
            return compile_result.returncode
        run_result = subprocess.run([str(executable), *arguments], check=False)
        return run_result.returncode


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "transpile":
            return _transpile(args.source, args.output)
        if args.command == "check":
            return _check(args.source)
        if args.command == "run":
            return _run(args.source, args.program_arguments)
        raise AssertionError(f"unknown command {args.command}")
    except (RubigoError, OSError, RuntimeError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
