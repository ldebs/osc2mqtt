# syntax=docker/dockerfile:1
# This Dockerfile is used to build a Docker image for the osc2mqtt_bridge application.
# It sets up a Python environment, installs dependencies, and runs the application.

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7

ARG PYTHON_VERSION=3.11.2
FROM python:${PYTHON_VERSION}-slim AS base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt && \
    mkdir -p /app/config && \
    chown -R appuser:appuser /app/config && \
    chmod -R 755 /app/config

# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container.
COPY *.py config.yaml.example .

VOLUME /app/config

# Expose the port that the application listens on.
EXPOSE 57272

# Run the application.
CMD ["python3", "-m", "osc2mqtt_bridge"]