import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "API")]

from shared.workspace import Workspace  # noqa: E402


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def usage(i=100, o=20, cr=0, cw=0):
    return NS(input_tokens=i, output_tokens=o, cache_read_input_tokens=cr, cache_creation_input_tokens=cw)


def text_resp(text, **u):
    return NS(content=[NS(type="text", text=text)], stop_reason="end_turn", usage=usage(**u))


def tool_resp(*calls, **u):
    blocks = [NS(type="tool_use", id=f"tu_{n}_{i}", name=n, input=a) for i, (n, a) in enumerate(calls)]
    return NS(content=blocks, stop_reason="tool_use", usage=usage(**u))


class FakeClient:
    """Scripted stand-in for anthropic.Anthropic(): no network, no key."""

    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.messages = NS(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if not self.script:
            raise AssertionError("fake client script exhausted")
        return self.script.pop(0)


@pytest.fixture
def ws(tmp_path):
    return Workspace.fresh(tmp_path / "ws")
