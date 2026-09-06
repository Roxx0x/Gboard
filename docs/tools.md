# Tools

A tool is a Python function plus a JSON schema. The registry turns your functions
into the `tools` payload the API expects and dispatches a tool call back to the
right function. Grok decides *when* to call; you decide *what* the tools are and
own running them.

## Writing one

```python
from gboard import default_registry, Agent

reg = default_registry()          # ships calc + now; start from empty with Registry()

@reg.tool(
    "weather",
    "Get the current weather for a city.",
    {"type": "object",
     "properties": {"city": {"type": "string"}},
     "required": ["city"]},
)
def weather(city: str) -> str:
    # call your real weather API here; return a string
    return f"{city}: 18C, clear"

agent = Agent(tools=reg)
print(agent.ask("what's the weather in Berlin?"))
```

The schema is standard JSON Schema — the same shape OpenAI-compatible function
calling uses. `required` matters: leave a field out of it and the model may omit
it, so your function needs a default or it'll be called with missing kwargs.

## The rules that keep it safe

**A tool returns a string.** The result goes straight back to the model as text.
Return something small and legible; a 50KB blob wastes context and confuses the
model.

**A tool must not crash the agent.** The registry wraps every call in a try/except
and hands the model `error running <tool>: ...` instead of raising. A flaky API or
bad arguments becomes a message the model can react to, not a dead process.

**Never `eval` model input.** The built-in `calc` looks like it could just
`eval()` the expression — and that's exactly how you hand a model (or a prompt
injection through it) arbitrary code execution. It walks an AST and permits only
arithmetic instead:

```python
reg.run("calc", {"expression": "2 + 3 * 4"})                    # "14"
reg.run("calc", {"expression": "__import__('os').system('...')"})  # "error: ..."
```

Any tool that touches a shell, a filesystem, or a query language needs the same
discipline: validate and constrain, never pass model output through unguarded.

## How the loop uses them

You don't call tools yourself. You register them and pass the registry to the
`Agent`; the loop sends their specs on every request, and when Grok returns a
tool call, the loop runs it and feeds the result back. The full round-trip is in
[architecture.md](architecture.md#the-loop-precisely). Grok may call several tools
across several steps before it answers — the step cap (`max_steps`, default 6)
bounds that so a confused model can't loop forever.
