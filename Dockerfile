FROM ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 AS uv

# Build stage
FROM python:3.15-slim-trixie@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913 AS builder

# Install uv
COPY --from=uv /uv /uvx /bin/

WORKDIR /app

# Compile bytecode for every installed package, embedding .pyc files in the image layer
ENV UV_COMPILE_BYTECODE=1 \
    # With Docker UV would copy anyway, explicit setting skips warnings
    UV_LINK_MODE=copy \
    # Disable development dependencies (--no-dev)
    UV_NO_DEV=1 \
    # Use ONLY system (here container) installed Python (--no-managed-python)
    UV_NO_MANAGED_PYTHON=1

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-editable

# Copy the project into the image
COPY . /app

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# Runtime stage
FROM python:3.15-slim-trixie@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

WORKDIR /app

# Copy the environment, but not the source code
COPY --from=builder /app/.venv /app/.venv

# Add the environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

ARG USER_NAME=non-root-user
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USER_NAME \
    && useradd --uid $USER_UID --gid $USER_GID --no-create-home $USER_NAME

# Set user
USER $USER_NAME

EXPOSE 8000

# Using Python standard library to health probe (no curl)
HEALTHCHECK CMD ["python",  "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"]

# Run the application
CMD ["gunicorn", "secure_messaging:create_app()", "--no-control-socket", "--bind", "0.0.0.0:8000"]
