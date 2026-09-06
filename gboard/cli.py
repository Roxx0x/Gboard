"""Command line interface. `gboard --help`."""

from __future__ import annotations

import argparse

from .agent import Agent
from .livesearch import search as build_search


def _agent(a) -> Agent:
    mode = "off" if a.no_search else a.search
    return Agent(system=a.system, search=build_search(mode), max_steps=a.max_steps)


def _render_trace(events: list[dict]) -> str:
    """The run, as a tree: each model call and tool, with real timing."""
    lines = []
    for e in events:
        if e["type"] == "model":
            tok = f"  {e['tokens']} tok" if e.get("tokens") else ""
            tail = (f"{len(e['tool_calls'])} tool call(s)" if e["tool_calls"] else "final answer")
            search = "  live search" if e["searched"] else ""
            lines.append(f"  step {e['step']}   {e['model']}{search}   {tail}{tok}   {e['latency']:.2f}s")
        elif e["type"] == "tool":
            lines.append(f"    tool  {e['name']:8} -> {e['result'][:40]}   {e['latency']:.2f}s")
        elif e["type"] == "done":
            lines.append(f"  done   {e['steps']} step(s)   {e['latency']:.2f}s")
    return "\n".join(lines)


def cmd_ask(a) -> int:
    agent = _agent(a)
    answer = agent.ask(a.message)
    if a.trace:
        print(f"> {a.message}")
        print(_render_trace(agent.last_trace))
        print()
    print(answer)
    return 0


def cmd_chat(a) -> int:
    agent = _agent(a)
    print("gboard chat — Ctrl-C to quit")
    try:
        while True:
            msg = input("\nyou > ").strip()
            if not msg:
                continue
            print(f"grok > {agent.ask(msg)}")
    except (KeyboardInterrupt, EOFError):
        print()
        return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gboard", description="A Grok agent: tools, live search, memory.")
    p.add_argument("--system", default="You are Grok, a terse and truthful assistant.")
    p.add_argument("--search", choices=["auto", "on", "off"], default="auto")
    p.add_argument("--no-search", action="store_true", help="shorthand for --search off")
    p.add_argument("--max-steps", type=int, default=6)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("ask", help="one-shot question")
    a.add_argument("message")
    a.add_argument("--trace", action="store_true", help="show the agent loop: steps, tools, timing")
    a.set_defaults(fn=cmd_ask)

    c = sub.add_parser("chat", help="interactive session")
    c.set_defaults(fn=cmd_chat)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
