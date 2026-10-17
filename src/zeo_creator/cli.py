"""Diagnostics and discovery only; workflow orchestration belongs to a runner."""

import importlib.metadata
import json
import sys
from enum import StrEnum
from pathlib import Path
from typing import Any

import typer

from zeo_creator import __version__
from zeo_creator.contract_schemas import (
    export_contract_schemas,
    list_contract_schemas,
    read_contract_schema,
)
from zeo_creator.registry import capability_manifests, openai_tool_projections
from zeo_creator.thread_lint import ThreadDraftError, lint_thread

app = typer.Typer(
    name="zeo-creator",
    help="Inspect ZEO Creator contracts and local compatibility.",
    add_completion=False,
)
contracts_app = typer.Typer(help="Discover and export packaged public contract schemas.")
app.add_typer(contracts_app, name="contracts")


# Zeocore's cli_protocol 1: stdout is JSON lines and nothing else, and the result is the
# last line, carrying "ok". Exit status: 0 done, 1 internal error, 2 invalid input or
# command, 20 held or refused (a failed check). Codes 10 to 13 concern remote operations,
# which this CLI never performs. runtime-provider is the one, time-limited exception: it
# keeps its canonical bytes until Runtime confirms a reader for the JSON-lines form.
CLI_PROTOCOL = "1"
EXIT_INTERNAL = 1
EXIT_INVALID = 2
EXIT_REFUSED = 20


class ProjectionFormat(StrEnum):
    MANIFEST = "manifest"
    OPENAI = "openai"


def _emit(kind: str, result: dict[str, object]) -> None:
    """Write the result as one JSON line, tagged with its versioned schema id."""
    tagged = {**result, "schema": f"zeocreator.{kind}/v1"}
    typer.echo(json.dumps(tagged, ensure_ascii=False, sort_keys=True))


def _version_callback(value: bool) -> None:
    if value:
        _emit("version", {"ok": True, "zeocreator": __version__, "cli_protocol": CLI_PROTOCOL})
        raise typer.Exit()


@app.callback()
def root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed version.",
    ),
) -> None:
    del version


@app.command()
def capabilities(
    projection: ProjectionFormat = typer.Option(
        ProjectionFormat.MANIFEST,
        "--projection",
        help="Render canonical manifests or OpenAI-compatible function tools.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Accepted; output is always JSON."),
) -> None:
    """List the stable continuous editorial and creator capabilities."""
    del json_output
    if projection == ProjectionFormat.OPENAI:
        tools = [item.model_dump(mode="json") for item in openai_tool_projections()]
        _emit("tools", {"ok": True, "tools": tools})
        return
    manifests = [item.model_dump(mode="json") for item in capability_manifests()]
    _emit("capabilities", {"ok": True, "capabilities": manifests})


@contracts_app.command("list")
def contracts_list(
    json_output: bool = typer.Option(False, "--json", help="Accepted; output is always JSON."),
) -> None:
    """List versioned contracts included in this installation."""
    del json_output
    rows = [
        {
            "name": item.name,
            "version": item.version,
            "filename": item.filename,
            "schema_digest": item.schema_digest,
        }
        for item in list_contract_schemas()
    ]
    _emit("contracts", {"ok": True, "contracts": rows})


@contracts_app.command("export")
def contracts_export(
    output: Path = typer.Option(..., "--output", help="Destination directory."),
) -> None:
    """Export packaged schemas without importing source checkout files."""
    written = export_contract_schemas(output)
    _emit("export", {"ok": True, "output": str(output), "files": len(written)})


@app.command("contract-schema")
def contract_schema(
    name: str = typer.Option(..., "--name", help="Stable contract name."),
    version: str = typer.Option(..., "--version", help="Contract major version."),
) -> None:
    """Print one packaged JSON Schema."""
    try:
        schema = read_contract_schema(name, version)
    except KeyError as exc:
        # The message names no input: an error never echoes what the caller sent.
        _emit("error", _invalid("unknown contract", "zeo-creator contracts list"))
        raise typer.Exit(EXIT_INVALID) from exc
    _emit("contract-schema", {"ok": True, "json_schema": schema})


@app.command()
def doctor(
    json_output: bool = typer.Option(False, "--json", help="Accepted; output is always JSON."),
) -> None:
    """Check the declared Python, Zeocore, manifest, and projection boundary."""
    zeocore_version = importlib.metadata.version("zeocore")
    checks = {
        "python_3_14_or_newer": sys.version_info >= (3, 14),
        "zeocore_0_18_0": zeocore_version == "0.18.0",
        "twenty_nine_manifests": len(capability_manifests()) == 29,
        "twenty_nine_openai_projections": len(openai_tool_projections()) == 29,
    }
    payload = {
        "ok": all(checks.values()),
        "python": ".".join(str(item) for item in sys.version_info[:3]),
        "zeocore": zeocore_version,
        "checks": checks,
        "next": [
            {"check": name, "next": DOCTOR_NEXT[name]} for name, ok in checks.items() if not ok
        ],
    }
    del json_output
    _emit("doctor", payload)
    if not payload["ok"]:
        raise typer.Exit(EXIT_REFUSED)


MAX_DRAFT_BYTES = 1_000_000


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """A JSON object with a repeated key is refused: readers disagree on which one wins."""
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ThreadDraftError("draft has a duplicate key")
    return dict(pairs)


@app.command("lint-thread")
def lint_thread_command(
    file: str = typer.Option(
        ..., "--file", help="A thread-draft/1 JSON file, or - to read standard input."
    ),
    json_output: bool = typer.Option(False, "--json", help="Accepted; output is always JSON."),
) -> None:
    """Lint a post thread: length, numbering, source, links, repetition. Offline and pure."""
    del json_output
    try:
        stream = sys.stdin.buffer if file == "-" else Path(file).open("rb")
        with stream:
            raw = stream.read(MAX_DRAFT_BYTES + 1)
        if len(raw) > MAX_DRAFT_BYTES:
            raise ThreadDraftError("draft is larger than 1 MB")
        draft = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
    except OSError, UnicodeDecodeError:
        _emit("error", _invalid("draft file could not be read", "check the --file path"))
        raise typer.Exit(EXIT_INVALID) from None
    except (ValueError, RecursionError) as exc:
        # Reading only: a bad number or nesting is the caller's input, not a linter fault.
        if isinstance(exc, ThreadDraftError):
            reason, step = str(exc), "fix the draft to match thread-draft/1"
        else:
            reason, step = "draft is not valid JSON", "pass one thread-draft/1 JSON object"
        _emit("error", _invalid(reason, step))
        raise typer.Exit(EXIT_INVALID) from None
    try:
        result = lint_thread(draft)
    except ThreadDraftError as exc:
        _emit("error", _invalid(str(exc), "fix the draft to match thread-draft/1"))
        raise typer.Exit(EXIT_INVALID) from None
    _emit("thread-lint", result)
    if not result["ok"]:
        raise typer.Exit(EXIT_REFUSED)


@app.command("runtime-provider")
def runtime_provider() -> None:
    """Emit canonical installed-provider JSON for trusted Runtime provisioning.

    Runtime supplies environment_digest and generation to form ProviderBinding.
    This is offline metadata preparation, not scoped discovery or authorization.
    Its bytes stay as they are, without "ok", until Runtime reads the JSON-lines form.
    """
    from zeo_core.adapters.runtime_host.canonical import canonical_bytes

    from zeo_creator.provider import provider_inventory

    typer.echo(canonical_bytes(provider_inventory()).decode())


EXIT_CODES = (
    (0, "done"),
    (EXIT_INTERNAL, "internal error; the result carries no detail"),
    (EXIT_INVALID, "invalid input or command; nothing was done"),
    (EXIT_REFUSED, "held or refused: a check failed"),
)
OUTPUT_SCHEMAS = {
    "help": ("zeocreator.help/v1",),
    "capabilities": ("zeocreator.capabilities/v1", "zeocreator.tools/v1"),
    "contracts list": ("zeocreator.contracts/v1",),
    "contracts export": ("zeocreator.export/v1",),
    "contract-schema": ("zeocreator.contract-schema/v1",),
    "doctor": ("zeocreator.doctor/v1",),
    "lint-thread": ("zeocreator.thread-lint/v1",),
    # The named exception to cli_protocol 1: one line of canonical inventory bytes.
    "runtime-provider": ("zeocreator.runtime-provider/canonical",),
}


def _options(command: Any) -> list[dict[str, object]]:
    options = []
    for param in command.params:
        if not getattr(param, "opts", None) or param.name == "help":
            continue
        choices = getattr(param.type, "choices", None)
        options.append(
            {
                "flags": list(param.opts),
                "type": param.type.name,
                "required": bool(param.required),
                "default": None if callable(param.default) else _jsonable(param.default),
                "choices": [str(item) for item in choices] if choices else None,
                "help": getattr(param, "help", None),
            }
        )
    return options


def _jsonable(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(getattr(value, "value", value))


def _commands(group: Any, prefix: str = "") -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for name, command in sorted(group.commands.items()):
        path = f"{prefix}{name}"
        if getattr(command, "commands", None) is not None:
            found.extend(_commands(command, f"{path} "))
            continue
        found.append(
            {
                "command": path,
                "summary": next(iter((command.help or "").strip().splitlines()), ""),
                "options": _options(command),
                "output_schemas": list(OUTPUT_SCHEMAS[path]),
            }
        )
    return found


@app.command("help")
def help_catalogue(
    json_output: bool = typer.Option(False, "--json", help="Accepted; output is always JSON."),
) -> None:
    """Print the machine catalogue: every command, option, exit code and output schema."""
    del json_output
    root_command = typer.main.get_command(app)
    _emit(
        "help",
        {
            "ok": True,
            "product": "zeocreator",
            "version": __version__,
            "cli_protocol": CLI_PROTOCOL,
            "global_options": _options(root_command),
            "commands": _commands(root_command),
            "exit_codes": [{"code": code, "meaning": meaning} for code, meaning in EXIT_CODES],
            "error_schema": "zeocreator.error/v1",
            "invalid_request_reasons": list(USAGE_REASONS),
            "version_schema": "zeocreator.version/v1",
        },
    )


# Each failing doctor check names the command that fixes it, or who must act.
_REINSTALL = f'uv tool install --force "zeocreator=={__version__}"'
DOCTOR_NEXT = {
    "python_3_14_or_newer": f"install Python 3.14 or newer, then run: {_REINSTALL}",
    "zeocore_0_18_0": 'run: uv pip install "zeocore[runtime-host]==0.18.0", or reinstall zeocreator',
    "twenty_nine_manifests": f"run: {_REINSTALL}; if it persists, report it to the zeocreator seat",
    "twenty_nine_openai_projections": (
        f"run: {_REINSTALL}; if it persists, report it to the zeocreator seat"
    ),
}
INTERNAL_NEXT = "rerun once; if it fails again, report the command to the zeocreator seat"


# The closed set of reasons an invalid request can give; help --json lists them.
USAGE_REASONS = (
    "unknown command",
    "missing command",
    "unknown option",
    "missing required option",
    "invalid option value",
    "unknown contract",
    "invalid command line",
)


def _invalid(reason: str, next_step: str) -> dict[str, object]:
    """An invalid-request result: a fixed reason and next step, never the caller's input."""
    return {"ok": False, "outcome": "invalid_request", "reason": reason, "next": next_step}


def _usage_reason(exc: Exception) -> str:
    # Typer's vendored Click names the problem by class; the reason is a fixed phrase,
    # so nothing the caller typed reaches stdout.
    kind = type(exc).__name__
    if kind == "NoSuchOption":
        return "unknown option"
    if kind == "MissingParameter":
        return "missing required option"
    if kind in {"BadParameter", "BadOptionUsage", "BadArgumentUsage"}:
        return "invalid option value"
    message = str(getattr(exc, "message", "")) or str(exc)
    if message.startswith("No such command"):
        return "unknown command"
    if message.startswith("Missing command"):
        return "missing command"
    return "invalid command line"


def _is_usage_error(exc: Exception) -> bool:
    # Typer vendors Click and exports no UsageError, so recognise it by its shape.
    return getattr(exc, "exit_code", None) == EXIT_INVALID and callable(getattr(exc, "show", None))


def main() -> None:
    try:
        code = app(standalone_mode=False)
    except Exception as exc:
        if _is_usage_error(exc):
            # Usage goes to stderr; stdout gets the result, which never echoes the input.
            exc.show()  # type: ignore[attr-defined]
            _emit("error", _invalid(_usage_reason(exc), "zeo-creator help --json"))
            sys.exit(EXIT_INVALID)
        # An internal error never echoes input or detail on stdout.
        _emit("error", {"ok": False, "outcome": "internal", "next": INTERNAL_NEXT})
        sys.exit(EXIT_INTERNAL)
    sys.exit(code if isinstance(code, int) else 0)


if __name__ == "__main__":
    main()
