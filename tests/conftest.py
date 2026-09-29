import pytest

# Env vars that move agent folders (registry/agents relocate entries). Tests use fixture homes only.
RELOCATION_VARS = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "XDG_CONFIG_HOME")


@pytest.fixture(autouse=True)
def _no_agent_relocation(monkeypatch):
    for var in RELOCATION_VARS:
        monkeypatch.delenv(var, raising=False)
