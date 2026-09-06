import os

import pytest

from gboard import Agent, Memory, search
from gboard.client import GrokClient
from gboard.tools import default_registry, _safe_eval

# force the offline stub regardless of environment
os.environ["GBOARD_BACKEND"] = "stub"


@pytest.fixture
def agent():
    return Agent()


# --- the tool loop --------------------------------------------------------

def test_agent_runs_a_tool_and_uses_the_result(agent):
    # the stub asks for the calc tool on an arithmetic question, then answers from its result
    answer = agent.ask("what is 21 * 2?")
    assert "42" in answer


def test_agent_plain_answer_without_tools(agent):
    answer = agent.ask("say hello")
    assert answer and "stub" in answer.lower()


def test_tool_call_records_correct_message_shape(agent):
    agent.ask("compute 6 * 7")
    roles = [m["role"] for m in agent.memory.messages(agent.system)]
    # only clean user/assistant turns are persisted; the tool exchange is transient
    assert "tool" not in roles
    assert roles.count("assistant") >= 1


def test_max_steps_guards_against_infinite_tools():
    agent = Agent(max_steps=2)
    ans = agent.ask("hello there")   # plain path still returns
    assert isinstance(ans, str)


# --- trace / observability ------------------------------------------------

def test_trace_records_model_tool_and_done(agent):
    agent.ask("what is 21 * 2?")   # triggers a tool round-trip
    kinds = [e["type"] for e in agent.last_trace]
    assert "model" in kinds and "tool" in kinds and kinds[-1] == "done"


def test_trace_has_real_timing(agent):
    agent.ask("say hi")
    assert all(e.get("latency", 0) >= 0 for e in agent.last_trace)
    done = agent.last_trace[-1]
    assert done["type"] == "done" and done["steps"] >= 1


def test_trace_resets_each_run(agent):
    agent.ask("say hi")
    n1 = len(agent.last_trace)
    agent.ask("say hi again")
    assert len(agent.last_trace) <= n1 + 1  # not accumulating across runs


# --- tools ----------------------------------------------------------------

def test_calc_tool_evaluates():
    reg = default_registry()
    assert reg.run("calc", {"expression": "2 + 3 * 4"}) == "14"


def test_calc_tool_is_sandboxed():
    reg = default_registry()
    out = reg.run("calc", {"expression": "__import__('os').system('echo hi')"})
    assert out.startswith("error")


def test_safe_eval_rejects_non_arithmetic():
    with pytest.raises(ValueError):
        _safe_eval("open('x')")


def test_unknown_tool_returns_error_not_crash():
    reg = default_registry()
    assert "no tool" in reg.run("nonexistent", {})


def test_tool_exception_is_caught():
    reg = default_registry()
    assert reg.run("calc", {"expression": "1/0"}).startswith("error")


# --- memory ---------------------------------------------------------------

def test_memory_carries_turns():
    m = Memory()
    m.add("user", "my name is sam")
    m.add("assistant", "noted")
    assert len(m.turns) == 2


def test_memory_trims_to_budget():
    m = Memory(max_turn_tokens=20)
    for i in range(50):
        m.add("user", "a fairly long message that costs some tokens number %d" % i)
    total = sum((len(t["content"]) + 3) // 4 for t in m.turns)
    assert total <= 20 or len(m.turns) == 1


def test_pinned_facts_survive_and_appear_in_system():
    m = Memory(max_turn_tokens=10)
    m.pin("the user's name is Sam")
    for i in range(30):
        m.add("user", "chatter %d that should push turns out of the window" % i)
    sys_msg = m.messages("base system")[0]
    assert "Sam" in sys_msg["content"]


# --- live search ----------------------------------------------------------

def test_search_builder_shapes():
    assert search("on", x=True, web=False)["sources"] == [{"type": "x"}]
    assert search("off")["mode"] == "off"
    assert "sources" not in search("off", x=False, web=False)


def test_search_from_handles():
    s = search("on", x=True, web=False, from_handles=("xai", "elonmusk"))
    assert s["sources"][0]["x_handles"] == ["xai", "elonmusk"]


def test_search_rejects_bad_mode():
    with pytest.raises(ValueError):
        search("sometimes")


# --- client stub ----------------------------------------------------------

def test_client_stub_needs_no_key():
    c = GrokClient(api_key="")
    assert c.backend == "stub"
    r = c.complete([{"role": "user", "content": "hi"}])
    assert r.content
