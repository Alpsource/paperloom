import yaml
from typer.testing import CliRunner

from paperloom import __version__
from paperloom.cli import app

runner = CliRunner()

TEMPLATE_FILES = [
    "README.md",
    "context.md",
    "index.md",
    "log.md",
    "CLAUDE.md",
    "sources/research/.gitkeep",
    "sources/contributors/.gitkeep",
    "sources/raw/.gitkeep",
    "artifacts/.gitkeep",
    "logs/.gitkeep",
]


def test_init_creates_template_and_config(tmp_path):
    vault = tmp_path / "myvault"
    result = runner.invoke(app, ["init", str(vault)])
    assert result.exit_code == 0, result.output

    for rel in TEMPLATE_FILES:
        assert (vault / rel).exists(), f"missing {rel}"

    config_path = vault / ".paperloom" / "config.yaml"
    assert config_path.exists()
    config = yaml.safe_load(config_path.read_text())
    assert config["template"] == "scientific-paper-vault"
    assert config["paperloom_version"] == __version__
    assert "created" in config


def test_init_initializes_git(tmp_path):
    vault = tmp_path / "gitvault"
    result = runner.invoke(app, ["init", str(vault)])
    assert result.exit_code == 0, result.output
    assert (vault / ".git").is_dir()


def test_init_refuses_overwrite_without_force(tmp_path):
    vault = tmp_path / "existingvault"
    first = runner.invoke(app, ["init", str(vault)])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["init", str(vault)])
    assert second.exit_code != 0
    assert "already exists" in second.output


def test_init_force_overwrites(tmp_path):
    vault = tmp_path / "forcevault"
    first = runner.invoke(app, ["init", str(vault)])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["init", str(vault), "--force"])
    assert second.exit_code == 0, second.output


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"paperloom {__version__}" in result.output
    assert "python 3." in result.output
