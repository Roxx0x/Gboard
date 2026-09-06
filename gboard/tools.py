"""
Tools the model can call, and the registry that runs them.

A tool is a plain Python function plus a JSON schema describing it. The registry
turns them into the `tools` payload the API expects, and dispatches a tool call
back to the function. Two safe demo tools ship (a calculator and a clock) so the
tool loop is real and testable out of the box; add your own with @tool.
"""

from __future__ import annotations

import ast
import operator
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict           # JSON schema for the arguments
    fn: Callable[..., str]

    def spec(self) -> dict:
        return {
            "type": "function",
            "function": {"name": self.name, "description": self.description, "parameters": self.parameters},
        }


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def add(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def tool(self, name: str, description: str, parameters: dict) -> Callable:
        def deco(fn: Callable[..., str]) -> Callable[..., str]:
            self.add(Tool(name=name, description=description, parameters=parameters, fn=fn))
            return fn
        return deco

    def specs(self) -> list[dict]:
        return [t.spec() for t in self._tools.values()]

    def run(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"error: no tool named {name!r}"
        try:
            return str(tool.fn(**arguments))
        except Exception as e:                      # a tool raising must not kill the agent
            return f"error running {name}: {e}"

    def __len__(self) -> int:
        return len(self._tools)


# --- a safe arithmetic evaluator for the calc tool ------------------------
# eval() on model-supplied strings is how you get owned. This walks an AST and
# only permits arithmetic, so "2+2" works and "__import__('os')" doesn't.

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(expr: str) -> float:
    def ev(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError("unsupported expression")
    return ev(ast.parse(expr, mode="eval").body)


def default_registry() -> Registry:
    r = Registry()

    @r.tool("calc", "Evaluate an arithmetic expression.",
            {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]})
    def calc(expression: str) -> str:
        return str(_safe_eval(expression))

    @r.tool("now", "Get the current UTC time in ISO format.",
            {"type": "object", "properties": {}})
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    return r
