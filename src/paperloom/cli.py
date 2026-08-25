"""Typer entry point. See §5 of paperloom.md for the full command surface."""

import sys
from datetime import date
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

import typer
import yaml
from rich.console import Console

from paperloom import __version__
from paperloom.ingest import IngestAborted, ingest_folder
from paperloom.search import RipgrepNotFoundError, hybrid_search
from paperloom.supervisor import spawn
from paperloom.vault import VaultNotFoundError, find_vault_root

app = typer.Typer(name="paperloom", help="Folder-scoped LLM-maintained research wiki.")
console = Console()

TEMPLATES_DIR = Path(__file__).parent / "templates"


@app.command()
def init(
    dir: Path = typer.Argument(Path("."), help="Directory to create the vault in (default: cwd)."),
    template: str = typer.Option("scientific-paper-vault", "--template", help="Template to copy."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing files."),
) -> None:
    """Create a new paperloom vault at DIR."""
    template_dir = TEMPLATES_DIR / template
    if not template_dir.is_dir():
        console.print(f"[red]Unknown template: {template}[/red]")
        raise typer.Exit(1)

    target = dir.resolve()
    target.mkdir(parents=True, exist_ok=True)

    for src in template_dir.rglob("*"):
        rel = src.relative_to(template_dir)
        dst = target / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
            continue
        if dst.exists() and not force:
            console.print(f"[red]{dst} already exists. Use --force to overwrite.[/red]")
            raise typer.Exit(1)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())

    paperloom_dir = target / ".paperloom"
    paperloom_dir.mkdir(exist_ok=True)
    config_path = paperloom_dir / "config.yaml"
    if not config_path.exists() or force:
        config_path.write_text(
            yaml.safe_dump(
                {
                    "template": template,
                    "created": date.today().isoformat(),
                    "paperloom_version": __version__,
                },
                sort_keys=False,
            )
        )

    if not (target / ".git").is_dir():
        try:
            proc = spawn(["git", "init"], cwd=str(target))
            proc.wait()
        except FileNotFoundError:
            console.print("[yellow]git not found on PATH — skipping git init.[/yellow]")

    console.print(f"[green]Vault created at {target}[/green]")


@app.command()
def ingest(
    folder: Path = typer.Argument(..., help="Folder to batch-ingest PDFs from."),
    pattern: str = typer.Option("*.pdf", "--pattern", help="Glob pattern for PDFs."),
    jobs: int = typer.Option(1, "--jobs", help="MinerU invocations to run in parallel."),
    skip_existing: bool = typer.Option(
        True, "--skip-existing/--no-skip-existing", help="Skip PDFs already ingested."
    ),
) -> None:
    """Batch-ingest every PDF in FOLDER matching --pattern."""
    try:
        vault_root = find_vault_root()
    except VaultNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    try:
        results = ingest_folder(
            folder, vault_root, pattern=pattern, jobs=jobs, skip_existing=skip_existing
        )
    except IngestAborted as e:
        console.print(f"[yellow]aborted after {e.completed}/{e.total} papers[/yellow]")
        raise typer.Exit(130) from None
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    succeeded = sum(1 for r in results if r.status == "success")
    skipped = sum(1 for r in results if r.status == "skipped")
    failed = sum(1 for r in results if r.status == "failed")
    console.print(
        f"[green]{succeeded} ingested[/green], {skipped} skipped, "
        f"[red]{failed} failed[/red] (of {len(results)})"
    )
    if failed:
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (literal text, not regex)."),
    top: int = typer.Option(10, "--top", help="Max results to show."),
) -> None:
    """Search the vault. Uses the same backend as the search MCP tool."""
    try:
        vault_root = find_vault_root()
    except VaultNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    try:
        hits = hybrid_search(vault_root, query, top_k=top)
    except RipgrepNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    if not hits:
        console.print("[yellow]No results.[/yellow]")
        return

    for hit in hits:
        console.print(f"[cyan]{hit.path}[/cyan]:[green]{hit.line}[/green]: {hit.snippet}")


@app.command()
def mcp() -> None:
    """Start the MCP server on stdio. Blocks. Ctrl-C to stop."""
    from paperloom.mcp_server import mcp as mcp_instance

    mcp_instance.run()


@app.command()
def version() -> None:
    """Print version, python version, key dependency versions."""
    console.print(f"paperloom {__version__}")
    console.print(f"python {sys.version.split()[0]}")
    for dep in ("typer", "rich", "PyYAML", "pydantic"):
        try:
            console.print(f"{dep} {pkg_version(dep)}")
        except PackageNotFoundError:
            console.print(f"{dep} (not installed)")


if __name__ == "__main__":
    app()
