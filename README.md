[![progress-banner](https://backend.codecrafters.io/progress/claude-code/0d8cd209-489a-4cac-8ee9-c861c4aab9d5)](https://app.codecrafters.io/users/Moath-COE?r=2qF)

This is a starting point for Python solutions to the
["Build Your own Claude Code" Challenge](https://codecrafters.io/challenges/claude-code).

Claude Code is an AI coding assistant that uses Large Language Models (LLMs) to
understand code and perform actions through tool calls. In this challenge,
you'll build your own Claude Code from scratch by implementing an LLM-powered
coding assistant.

Along the way you'll learn about HTTP RESTful APIs, OpenAI-compatible tool
calling, agent loop, and how to integrate multiple tools into an AI assistant.

**Note**: If you're viewing this repo on GitHub, head over to
[codecrafters.io](https://codecrafters.io) to try the challenge.

# Passing the first stage

The entry point for your `claude-code` implementation is in `app/main.py`. Study
and uncomment the relevant code, and submit to pass the first stage:

```sh
codecrafters submit
```

# Running locally in a container

Once the agent has a `Bash` tool, the model can run arbitrary commands. To keep
that away from your real machine, run the agent inside a container. The project
is mounted **read-only**, with one writable folder, `agent_workspace/`. This is for
local development only. CodeCrafters doesn't use it, and everything lives in
`docker/`.

```sh
# From the project root. Opens a shell inside the container.
./dev.sh
```

The shell starts in `/workspace/agent_workspace`, so any relative path the agent
writes lands there. Inside the container:

```sh
/workspace/your_program.sh -p "create a file named hello.txt"  # run the agent
cd /workspace && uv run pytest                                 # tests
```

Or run a single command without opening a shell:

```sh
./dev.sh uv run --project /workspace pytest /workspace
```

Notes:

- Edit code on your host as usual. The container sees your edits immediately.
- The container can't change the project, so run `ruff format`, `git` and
  `codecrafters submit` on your host.
- The agent can read your source with absolute paths (`/workspace/app/...`),
  but it can only write inside `agent_workspace/`. Prompts that name a path in the
  project root will get a "read-only file system" error.
- Keep `agent_workspace/` for throwaway files. The agent may overwrite or delete
  what's in it.
- The first run builds the image. Rebuild after editing the Dockerfile with
  `docker compose -f docker/compose.yml build`.
- File ownership: the image uses UID/GID 1000. If `id -u` on your host differs,
  build with `HOST_UID=$(id -u) HOST_GID=$(id -g) docker compose -f docker/compose.yml build`.
- Your `.env` is loaded as environment variables, and the file itself is hidden
  inside the container.
- The compose file sets `UV_FROZEN`, `RUFF_CACHE_DIR` and
  `PYTEST_ADDOPTS` so uv, ruff and pytest don't try to write into the
  read-only project.

What this does and doesn't protect against:

- The container can't modify your code, your git history or anything outside
  the project. It runs as a non-root user with all Linux capabilities dropped.
- `agent_workspace/` is writable, so a bad command can still wipe it.
- The network is open, because the agent needs to reach OpenRouter. The API key
  is in the container's environment, so a command that runs `env` can read it.
  Use a key with a low spending limit.
- This is a safety net, not a hardened sandbox.

# Stage 2 & beyond

Note: This section is for stages 2 and beyond.

1. Ensure you have `uv` installed locally.
2. Run `./your_program.sh` to run your program, which is implemented in
   `app/main.py`.
3. Run `codecrafters submit` to submit your solution to CodeCrafters. Test
   output will be streamed to your terminal.
