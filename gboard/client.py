"""
A thin xAI (Grok) client. Standard library only — no SDK.

The xAI API is OpenAI-compatible: a POST to /v1/chat/completions with a Bearer
key. That's a urllib call, so there's no reason to pull in a dependency for it.
This wraps that call, normalises the response into something the agent loop can
read, and adds two Grok-specific things the base OpenAI shape doesn't have:
live search parameters, and a stub backend so the whole package runs, and tests,
with no key and no network.

Set XAI_API_KEY and GBOARD_BACKEND=xai to talk to the real thing.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

BASE_URL = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1")
DEFAULT_MODEL = os.environ.get("GBOARD_MODEL", "grok-4")


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class Response:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class GrokClient:
    def __init__(self, api_key: str | None = None, *, model: str = DEFAULT_MODEL, timeout: float = 60.0) -> None:
        self.api_key = api_key or os.environ.get("XAI_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self.backend = os.environ.get("GBOARD_BACKEND", "stub" if not self.api_key else "xai")

    def complete(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        search: dict | None = None,
        model: str | None = None,
    ) -> Response:
        if self.backend == "stub":
            return _stub_complete(messages, tools=tools, search=search)
        if self.backend == "xai":
            return self._xai_complete(messages, tools=tools, search=search, model=model)
        raise ValueError(f"unknown GBOARD_BACKEND={self.backend!r}")

    def _xai_complete(self, messages, tools, search, model) -> Response:
        body: dict = {"model": model or self.model, "messages": messages}
        if tools:
            body["tools"] = tools
        if search is not None:
            body["search_parameters"] = search  # Grok Live Search; see livesearch.py
        req = urllib.request.Request(
            f"{BASE_URL}/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            raise RuntimeError(f"xAI API {e.code}: {detail}") from None
        return _parse(data)


def _parse(data: dict) -> Response:
    """OpenAI-compatible response → our Response."""
    msg = data.get("choices", [{}])[0].get("message", {})
    calls = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function", {})
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        calls.append(ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args or {}))
    return Response(content=msg.get("content"), tool_calls=calls, raw=data)


# --- offline stub ---------------------------------------------------------
# Deterministic, dependency-free. It exists so the agent loop runs and is tested
# without a key: it recognises when a tool would help and asks for it, then
# answers using the tool result on the next turn. The behaviour mirrors the real
# tool-calling round-trip, which is the part worth testing offline.

def _last_user(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content") or ""
    return ""


def _has_tool_result(messages: list[dict]) -> bool:
    return any(m.get("role") == "tool" for m in messages)


def _stub_complete(messages, tools=None, search=None) -> Response:
    user = _last_user(messages).lower()
    tool_names = {t.get("function", {}).get("name") for t in (tools or [])}

    # if a tool result is already present, synthesise a final answer from it
    if _has_tool_result(messages):
        last_tool = next(m for m in reversed(messages) if m.get("role") == "tool")
        return Response(content=f"[grok-stub] Based on the tool result: {last_tool.get('content')}")

    # otherwise, decide whether to call a tool
    if "calc" in tool_names and any(c.isdigit() for c in user) and any(op in user for op in "+-*/"):
        expr = "".join(c for c in _last_user(messages) if c in "0123456789+-*/(). ")
        return Response(tool_calls=[ToolCall(id="stub-1", name="calc", arguments={"expression": expr.strip()})])
    if "now" in tool_names and "time" in user:
        return Response(tool_calls=[ToolCall(id="stub-2", name="now", arguments={})])

    hint = " (live search would run here)" if search and search.get("mode") != "off" else ""
    return Response(content=f"[grok-stub] {(_last_user(messages) or 'hello').strip()[:120]}{hint}")
