# Live search

The reason to build an agent on Grok specifically. Grok can ground a response in
real-time X (Twitter) and the web at request time — no vector store, no crawler,
no retrieval pipeline of yours. You ask; it looks things up while answering.

You turn it on with `search_parameters` on the request. `livesearch.search()`
builds that object.

```python
from gboard import Agent, search

# let the model decide when fresh data is needed (the default)
agent = Agent(search=search("auto"))

# force search, X only, from specific accounts
agent = Agent(search=search("on", x=True, web=False, from_handles=("xai", "elonmusk")))

# turn it off for a plain completion
agent = Agent(search=search("off"))
```

## Modes

| mode | behaviour |
|---|---|
| `auto` | the model decides whether the query needs fresh data — the sane default |
| `on` | always search |
| `off` | never search; a plain completion |

`auto` is right for most agents: "what is 2+2" shouldn't trigger a search, "what
did xAI announce today" should, and the model is good at telling them apart.
Forcing `on` everywhere is slower and costs more; forcing `off` throws away the
one thing Grok does that other models can't.

## Sources

`search()` lets you scope where it looks:

- `x=True` — real-time posts on X. Add `from_handles=(...)` to restrict to
  specific accounts, which is how you build "what is @xai saying" agents.
- `web=True` — the open web.
- `news=True` — news sources.
- `max_results=N` — cap how many sources it pulls, to bound latency and cost.

Leaving sources broad lets Grok choose; narrowing them makes answers more focused
and cheaper.

## When it matters

Live search is the difference between an assistant that knows the world as of its
training cut-off and one that knows what happened an hour ago. For anything
tracking releases, prices, sentiment, breaking events, or a specific person's
posts, it's the whole point. For timeless questions — math, code, definitions —
leave it on `auto` and it'll stay out of the way.

## Cost and latency

Search adds a round-trip to fetch sources before the model answers, so a searched
response is slower and pricier than a plain one. `auto` keeps that cost off the
questions that don't need it. If you're on a tight latency budget for a known
class of queries, set `off` explicitly rather than paying for `auto` to decide.
