"""
gboard — a real Grok agent in a few hundred lines of standard library.

Not a prompt dump and not a web-scraping "free Grok" wrapper. The agent loop on
the official xAI API, with the parts tutorials skip: tool calling, Grok's live
search over real-time X and the web, conversation memory, and a stub backend so
it runs offline.

    from gboard import Agent

    agent = Agent(system="You are terse and accurate.")
    print(agent.ask("what is 21 * 2?"))     # uses the calc tool
"""

from .agent import Agent
from .client import GrokClient, Response, ToolCall
from .livesearch import search
from .memory import Memory
from .tools import Registry, Tool, default_registry

__version__ = "0.1.0"
__all__ = [
    "Agent", "GrokClient", "Response", "ToolCall",
    "Registry", "Tool", "default_registry", "Memory", "search", "__version__",
]
