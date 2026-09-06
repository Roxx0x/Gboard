"""
Live Search — the reason to build on Grok instead of anything else.

Grok can ground an answer in real-time X (Twitter) and the web at request time,
without you running a separate retrieval pipeline. You turn it on by passing
`search_parameters` in the chat request; this module builds that object so you
don't have to memorise the shape.

`mode`:
  "auto" — the model decides whether a query needs fresh data (the sane default)
  "on"   — always search
  "off"  — never search (plain completion)

`sources` narrows where it looks: X, the web, news, or specific handles. Leaving
it empty lets Grok choose across everything it has.
"""

from __future__ import annotations


def search(
    mode: str = "auto",
    *,
    x: bool = True,
    web: bool = True,
    news: bool = False,
    from_handles: tuple[str, ...] = (),
    max_results: int | None = None,
) -> dict:
    """Build a `search_parameters` object for a Grok request.

    >>> search("on", x=True, web=False)["sources"]
    [{'type': 'x'}]
    """
    if mode not in ("auto", "on", "off"):
        raise ValueError("mode must be auto, on, or off")

    sources: list[dict] = []
    if x:
        src: dict = {"type": "x"}
        if from_handles:
            src["x_handles"] = list(from_handles)
        sources.append(src)
    if web:
        sources.append({"type": "web"})
    if news:
        sources.append({"type": "news"})

    params: dict = {"mode": mode}
    if sources:
        params["sources"] = sources
    if max_results is not None:
        params["max_search_results"] = max_results
    return params


OFF = {"mode": "off"}
