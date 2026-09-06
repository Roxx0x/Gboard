"""
Conversation memory — a small, honest default.

An agent that forgets the last thing you said isn't an agent, it's a form. This
keeps the running turn history within a token-ish budget and lets you pin durable
facts that should survive trimming ("the user's name is Sam"). It's deliberately
simple; for real long-term memory — decay, association, consolidation — point the
agent at a proper store. The interface is two methods, so swapping it is trivial.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _approx_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


@dataclass
class Memory:
    max_turn_tokens: int = 3000          # trim old turns past this; keeps recent context cheap
    turns: list[dict] = field(default_factory=list)
    pinned: list[str] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.turns.append({"role": role, "content": content})
        self._trim()

    def pin(self, fact: str) -> None:
        """Mark a fact durable. Pinned facts ride in the system context and are
        never trimmed — the small set of things the agent must not forget."""
        if fact not in self.pinned:
            self.pinned.append(fact)

    def _trim(self) -> None:
        # drop oldest turns (never the very last user turn) until under budget
        total = sum(_approx_tokens(t["content"]) for t in self.turns)
        while total > self.max_turn_tokens and len(self.turns) > 1:
            dropped = self.turns.pop(0)
            total -= _approx_tokens(dropped["content"])

    def messages(self, system: str = "") -> list[dict]:
        """Assemble the message list for a request: system prompt + pinned facts,
        then the trimmed turn history."""
        sys_parts = [p for p in [system] if p]
        if self.pinned:
            sys_parts.append("Known facts:\n" + "\n".join(f"- {f}" for f in self.pinned))
        msgs: list[dict] = []
        if sys_parts:
            msgs.append({"role": "system", "content": "\n\n".join(sys_parts)})
        msgs.extend(self.turns)
        return msgs
