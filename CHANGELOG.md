# Changelog

## 0.1.0

- Agent loop over the official xAI API with iterative tool calling and a step cap
- Live search integration (`auto` / `on` / `off`, scoped to X / web / news / handles)
- Tool registry with a decorator API; sandboxed `calc` (AST, no eval) and `now`
- Conversation memory: trimmed turn history plus pinned facts
- Zero-dependency xAI client on `urllib`; offline stub backend for keyless runs
- Per-run trace (`self.last_trace`): one event per model call and tool, with real
  wall-clock timing and token counts when the API reports them
- `gboard` CLI: `ask` (with `--trace`) and `chat`
- Visual README with architecture and sequence diagrams
