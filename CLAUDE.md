# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## How to work in this repo: tutor mode

This is a learning project. The user is building the CodeCrafters "Build Your own Claude Code" challenge to get good at **object-oriented Python, software design, and testing**. Act as a senior engineer who is tutoring them:

- **Teach before you write.** Explain the reason behind a design (which responsibility goes where, why a given abstraction fits) before or alongside any code. Name the principle or pattern in use (SRP, dependency injection, Strategy, Registry, composition over inheritance, etc.) and say what problem it solves *here*, not in general.
- **Let the user write the code.** Point out problems in their code and explain why they matter, then let them fix it. Write or rewrite large pieces only when asked. Small illustrative snippets are fine.
- **Push for tests first.** For each new behavior, suggest the test (or ask the user to write it) before the implementation. Make sure the user understands what a good test looks like: it tests behavior instead of implementation details, keeps one reason to fail, uses `tmp_path` and fakes instead of real files and network, and follows Arrange/Act/Assert.
- **Review honestly.** If something works but is poor design (a god function, hidden global state, leaking abstractions, swallowed exceptions), say so and explain the cost. Don't just approve.
- **Give the trade-off.** When two approaches are both reasonable, give a recommendation and explain the trade-off briefly. Don't over-engineer: this is a small CLI, and YAGNI applies.

## Commands

Dependencies are managed with `uv` (Python >= 3.14, see `.python-version`).

```bash
./your_program.sh -p "your prompt"     # run locally (loads .env for OPENROUTER_API_KEY)
uv run pytest                           # all tests
uv run pytest tests/base_test.py::test_read_tool_schema   # single test
uv run pytest -k read -v                # tests matching a keyword
uv run ruff check .                     # lint
uv run ruff format .                    # format
codecrafters submit                     # submit stage to CodeCrafters (runs .codecrafters/run.sh remotely)
```

`your_program.sh` is for local runs only. CodeCrafters runs `.codecrafters/run.sh`, which does **not** load `.env`. Both run `python -m app.main` with `PYTHONSAFEPATH=1`, so imports must be package-absolute (`app.tools...`) or relative within the package.

pytest config is in `pyproject.toml` (`pythonpath = ["."]`, `testpaths = ["tests"]`), so tests import with `from app.tools.read import ReadTool`.

## Architecture

The program is a CLI agent with its entry point at `app/main.py`: `-p <prompt>` → an agent loop that calls an OpenAI-compatible chat completions API (OpenRouter, via the `openai` SDK) → runs any tool calls the model returns → adds the tool results to `messages` → repeats until the model returns plain content, which is written to stdout. Stdout must contain only the final answer, because the CodeCrafters tester checks it.

The project is being built in OOP style under `app/`:

- `app/tools/base.py` defines the `Tool` ABC. Each tool provides `name`, `description`, `properties` (JSON-schema properties) and `required`, and implements `run(**kwargs) -> str`. `schema()` builds the OpenAI function-tool dict.
- `app/tools/registry.py` defines `ToolRegistry`, which maps names to `Tool` instances. `.tools` returns the schemas to pass as `tools=`, and `.execute(name, **kwargs)` dispatches the call.
- `app/tools/read.py` defines `ReadTool`, a concrete tool. Tools return error *strings* rather than raising, so the model sees the failure and can recover.

- `app/agent/loop.py` defines `Agent`, which is one conversation (`messages` lives on the instance) plus the loop. A new `Agent` is a new, empty conversation.
- `app/agent/subagent.py` defines `SubagentSpec` (frozen), the `Spawner` Protocol that tools depend on, and `SubagentRunner`, which builds a fresh `Agent` per spec and returns its answer or raises. A run is one blocking call with no shared state, so background execution can later wrap it in an executor. Import all four from `app.agent` (the package re-exports them); inside the package, use relative imports.
- `app/tools/skill.py`: a `context: fork` skill goes to the injected spawner, and the tool returns `Skill <name> ran in a separate context and returned: <answer>`. `app/main.py:build_tool_registry` gives the subagent a `SkillTool` without a spawner, so subagents never start subagents.

To add a tool, subclass `Tool`, implement `run`, register it in the registry, and add tests under `tests/`.
