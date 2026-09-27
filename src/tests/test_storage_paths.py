"""Regresi: CHROMADB_PERSIST_DIR berisi path container (/app/...) di host → Read-only file system."""

from storage_paths import resolve_chroma_dir


def test_default_when_env_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("CHROMADB_PERSIST_DIR", raising=False)
    assert resolve_chroma_dir(tmp_path / "default") == tmp_path / "default"


def test_env_used_when_writable(monkeypatch, tmp_path):
    target = tmp_path / "custom" / "chroma_db"
    monkeypatch.setenv("CHROMADB_PERSIST_DIR", str(target))
    assert resolve_chroma_dir(tmp_path / "default") == target
    assert target.is_dir()


def test_falls_back_when_env_path_unusable(monkeypatch, tmp_path, capsys):
    blocker = tmp_path / "bukan_folder"
    blocker.write_text("x")                      # parent berupa file → mkdir gagal (OSError)
    monkeypatch.setenv("CHROMADB_PERSIST_DIR", str(blocker / "chroma_db"))
    assert resolve_chroma_dir(tmp_path / "default") == tmp_path / "default"
    assert "tidak dapat dipakai" in capsys.readouterr().out
