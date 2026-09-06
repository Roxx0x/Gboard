"""
gboard in one screen: a tool call, memory across turns, and live search wired in.

Runs on the offline stub so it works with no key. Set XAI_API_KEY and
GBOARD_BACKEND=xai to see the real model (and real live search) answer.

    python examples/demo.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("GBOARD_BACKEND", "stub")

from gboard import Agent, search

agent = Agent(
    system="You are Grok, terse and accurate.",
    search=search("auto", x=True, web=True),   # ground answers in real-time X + web
)

# a tool call: the model asks for calc, gboard runs it, the model answers from the result
print("Q: what is 128 * 12?")
print("A:", agent.ask("what is 128 * 12?"))

# memory: the second turn can rely on the first
print("\nQ: remember that my project is called gboard")
print("A:", agent.ask("remember that my project is called gboard"))
agent.memory.pin("the user's project is called gboard")

# a plain, search-eligible question
print("\nQ: what are people saying about xAI this week?")
print("A:", agent.ask("what are people saying about xAI this week?"))

print("\n(the stub narrates where live search would run; the real backend actually runs it)")
