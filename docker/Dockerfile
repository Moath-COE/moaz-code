# Local development container. NOT used by CodeCrafters (it builds from
# codecrafters.yml). The project is mounted at runtime, never copied in, so
# neither your code nor your .env end up inside the image.
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

# Match your host user so files written through the mount aren't owned by root.
ARG UID=1000
ARG GID=1000

RUN groupadd --gid "${GID}" dev \
    && useradd --uid "${UID}" --gid "${GID}" --create-home dev \
    && mkdir /opt/venv /workspace \
    && chown dev:dev /opt/venv /workspace

# The venv lives outside the mount so it never touches your host .venv.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1

RUN printf '#!/bin/sh\nexec /workspace/your_program.sh -p "$@"\n' > /usr/local/bin/mcode \
    && chmod +x /usr/local/bin/mcode

USER dev
WORKDIR /workspace
CMD ["bash"]
