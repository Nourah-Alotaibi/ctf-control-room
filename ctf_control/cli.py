from pathlib import Path
import typer
from .app import ControlRoom

app = typer.Typer(add_completion=False, help="CTF Control Room")

@app.command()
def main(
    root: Path = typer.Argument(
        Path.cwd(),
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
        help="CTF root containing category folders."
    ),
    agent: str = typer.Option("codex", "--agent", "-a", help="Default terminal agent.")
):
    """Open the terminal CTF control room."""
    ControlRoom(ctf_root=root, default_agent=agent).run()

if __name__ == "__main__":
    app()
