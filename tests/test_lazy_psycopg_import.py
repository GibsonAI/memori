import builtins
import importlib
import os
import pytest


def test_import_without_psycopg(monkeypatch):
    """Ensure importing the package works even when psycopg is not installed."""
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "psycopg" or name.startswith("psycopg."):
            raise ImportError("No module named 'psycopg'")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # Import should succeed because psycopg is only required when using default connection
    importlib.invalidate_caches()
    memori = importlib.import_module("memori")

    assert hasattr(memori, "Memori")


def test_default_connection_requires_psycopg(monkeypatch):
    """If MEMORI_COCKROACHDB_CONNECTION_STRING is set, importing and instantiating Memori should raise a clear error when psycopg is missing."""
    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "psycopg" or name.startswith("psycopg."):
            raise ImportError("No module named 'psycopg'")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setenv("MEMORI_COCKROACHDB_CONNECTION_STRING", "postgresql://user:pass@localhost/db")
    monkeypatch.setattr(builtins, "__import__", fake_import)

    importlib.invalidate_caches()
    memori = importlib.import_module("memori")

    with pytest.raises(RuntimeError) as e:
        memori.Memori()

    assert "psycopg is required" in str(e.value)
