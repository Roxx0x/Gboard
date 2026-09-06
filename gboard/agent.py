"""
The agent loop. This is the whole thing.

A message comes in. Grok answers — or asks to run a tool, in which case we run it,
hand back the result, and let Grok continue, until it has a final answer or hits
the step cap. Live search rides on every model call so answers can be grounded in
real-time X and the web. Memory carries the conversation across turns.

    from gboard import Agent

    agent = Agent(system="You are a terse, accurate assistant.")
    print(agent.ask("what is known about the latest xAI release?"))

Runs offline on the stub with no key; set XAI_API_KEY for the real model.
"""

from __future__ import annotations

import time

from .client import GrokClient, Response
from .livesearch import search as build_search
from .memory import Memory
from .tools import Registry, default_registry


class Agent:
    def __init__(
        self,
        *,
        system: str = "You are Grok, a helpful and maximally truthful assistant.",
        client: GrokClient | None = None,
        tools: Registry | None = None,
        memory: Memory | None = None,
        search: dict | None = None,
        max_steps: int = 6,
    ) -> None:
        self.system = system
        self.client = client or GrokClient()
        self.tools = tools if tools is not None else default_registry()
        self.memory = memory or Memory()
        self.search = search if search is not None else build_search("auto")
        self.max_steps = max_steps
        self.last_trace: list[dict] = []   # events from the most recent ask(); see --trace

    def ask(self, message: str) -> str:
        """Run one user turn to completion, tools and all. Returns the final text.

        Every run records a trace on `self.last_trace`: one event per model call
        and tool run, with real wall-clock timing (and token counts when the API
        reports them). `gboard ask --trace` renders it. It's real observability,
        not a log — the exact sequence and cost of the loop, per turn.
        """
        self.last_trace = []
        t0 = time.perf_counter()
        searched = bool(self.search and self.search.get("mode") != "off")
        self.memory.add("user", message)
        # working messages = persisted history + this turn's transient tool exchange
        messages = self.memory.messages(self.system)
        tool_specs = self.tools.specs() if len(self.tools) else None

        for step in range(1, self.max_steps + 1):
            ts = time.perf_counter()
            resp: Response = self.client.complete(messages, tools=tool_specs, search=self.search)
            self.last_trace.append({
                "type": "model", "step": step, "model": self.client.model,
                "latency": time.perf_counter() - ts,
                "searched": searched,
                "tool_calls": [tc.name for tc in resp.tool_calls],
                "tokens": (resp.raw.get("usage") or {}).get("total_tokens"),
            })

            if not resp.wants_tools:
                self.last_trace.append({"type": "done", "steps": step, "latency": time.perf_counter() - t0})
                answer = resp.content or ""
                self.memory.add("assistant", answer)
                return answer

            # record the assistant's tool request in API-correct shape, then run each tool
            messages.append({
                "role": "assistant",
                "content": resp.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.name, "arguments": _dumps(tc.arguments)}}
                    for tc in resp.tool_calls
                ],
            })
            for tc in resp.tool_calls:
                tts = time.perf_counter()
                result = self.tools.run(tc.name, tc.arguments)
                self.last_trace.append({
                    "type": "tool", "name": tc.name, "result": result,
                    "latency": time.perf_counter() - tts,
                })
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        # ran out of steps: return the best content we have rather than looping forever
        self.last_trace.append({"type": "done", "steps": self.max_steps, "latency": time.perf_counter() - t0})
        fallback = "I couldn't finish within the step budget."
        self.memory.add("assistant", fallback)
        return fallback


def _dumps(obj: dict) -> str:
    import json
    return json.dumps(obj)
