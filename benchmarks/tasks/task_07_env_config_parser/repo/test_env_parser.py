import os
from env_parser import parse_env_var

def test_string_env(monkeypatch):
    monkeypatch.setenv("APP_NAME", "TerminalAgent")
    assert parse_env_var("APP_NAME", str) == "TerminalAgent"

def test_integer_env(monkeypatch):
    monkeypatch.setenv("PORT", "8080")
    assert parse_env_var("PORT", int) == 8080

def test_boolean_env(monkeypatch):
    monkeypatch.setenv("DEBUG_TRUE", "true")
    monkeypatch.setenv("DEBUG_FALSE", "0")
    assert parse_env_var("DEBUG_TRUE", bool) is True
    assert parse_env_var("DEBUG_FALSE", bool) is False

def test_default_fallback(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    assert parse_env_var("MISSING_KEY", int, default=42) == 42
