from pathlib import Path

import pytest

from paperloom.vault import VaultNotFoundError, find_vault_root


def make_vault(root: Path) -> Path:
    (root / ".paperloom").mkdir(parents=True)
    return root


def test_find_vault_root_when_cwd_is_vault_root(tmp_path):
    vault = make_vault(tmp_path / "myvault")
    assert find_vault_root(start=vault) == vault


def test_find_vault_root_walks_up_from_nested_subdir(tmp_path):
    vault = make_vault(tmp_path / "myvault")
    nested = vault / "sources" / "research" / "methods"
    nested.mkdir(parents=True)
    assert find_vault_root(start=nested) == vault


def test_find_vault_root_raises_outside_any_vault(tmp_path):
    # An isolated tree under tmp_path with no .paperloom/ anywhere in it or
    # its ancestors up to tmp_path itself.
    stray = tmp_path / "not-a-vault" / "some" / "dir"
    stray.mkdir(parents=True)
    with pytest.raises(VaultNotFoundError):
        find_vault_root(start=stray)


def test_find_vault_root_vault_dir_override(tmp_path):
    vault = make_vault(tmp_path / "explicit-vault")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    # Even though cwd-equivalent `start` isn't inside the vault, the
    # explicit override should resolve directly to it.
    assert find_vault_root(start=elsewhere, vault_dir=vault) == vault


def test_find_vault_root_vault_dir_override_raises_if_not_a_vault(tmp_path):
    not_a_vault = tmp_path / "plain-dir"
    not_a_vault.mkdir()
    with pytest.raises(VaultNotFoundError):
        find_vault_root(vault_dir=not_a_vault)
