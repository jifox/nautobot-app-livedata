# -------------------------------------------------------------------------------------
# Nautobot App Developement Dockerfile Template
# Version: 1.1.0
#
# Apps that need to add additional steps or packages can do in the section below.
# -------------------------------------------------------------------------------------
# !!! USE CAUTION WHEN MODIFYING LINES BELOW

# Accepts a desired Nautobot version as build argument, default to 2.4.0
ARG NAUTOBOT_VER="2.4.0"

# Accepts a desired Python version as build argument, default to 3.11
ARG PYTHON_VER="3.11"

# Retrieve published development image of Nautobot base which should include most CI dependencies
FROM ghcr.io/nautobot/nautobot-dev:${NAUTOBOT_VER}-py${PYTHON_VER}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Runtime argument and environment setup
ARG NAUTOBOT_ROOT=/opt/nautobot

ENV prometheus_multiproc_dir=/prom_cache
ENV NAUTOBOT_ROOT=${NAUTOBOT_ROOT}
ENV INVOKE_NAUTOBOT_APP_LIVEDATA_LOCAL=true

# Install Poetry manually via its installer script;
# We might be using an older version of Nautobot that includes an older version of Poetry
# and CI and local development may have a newer version of Poetry
# Since this is only used for development and we don't ship this container, pinning Poetry back is not expressly necessary
# We also don't need virtual environments in container
RUN if ! command -v poetry >/dev/null 2>&1; then \
        curl -sSL https://install.python-poetry.org | python3 -; \
    fi; \
    poetry config virtualenvs.create false; \
    poetry self add poetry-plugin-export || true \
    poetry self add poetry-plugin-shell || true

# !!! USE CAUTION WHEN MODIFYING LINES ABOVE
# -------------------------------------------------------------------------------------
# App-specifc system build/test dependencies.
#
# Example: LDAP requires `libldap2-dev` to be apt-installed before the Python package.
# -------------------------------------------------------------------------------------
# --> Start safe to modify section

# Uncomment the lines below if you are apt-installing any package.
# RUN apt-get -y update && apt-get -y install \
#     libldap2-dev \
#     && rm -rf /var/lib/apt/lists/*

# --> Stop safe to modify section
# -------------------------------------------------------------------------------------
# Install Nautobot App
# -------------------------------------------------------------------------------------
# !!! USE CAUTION WHEN MODIFYING LINES BELOW

# Copy in the source code
WORKDIR /source
COPY . /source

# Build args must be declared in each stage
ARG NAUTOBOT_VER
ARG PYTHON_VER

# Pin Nautobot in the lock file BEFORE any install step, so poetry install
# never resolves a newer patch release only to downgrade it afterwards.
# If NAUTOBOT_VER is a channel/tag like "stable", resolve it to the version
# already installed in the selected base image.
# In CI this should be done outside the Dockerfile to prevent cross-compile build failures.
ARG CI
RUN if [ -z "${CI+x}" ]; then \
        RESOLVED_NAUTOBOT_VER="${NAUTOBOT_VER}"; \
        if ! [[ "${NAUTOBOT_VER}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([A-Za-z0-9.+-]*)?$ ]]; then \
            RESOLVED_NAUTOBOT_VER="$(pip show nautobot | awk -F': ' '/^Version:/{print $2}')"; \
            if [ -z "${RESOLVED_NAUTOBOT_VER}" ]; then \
                echo "Unable to resolve Nautobot version from base image for NAUTOBOT_VER=${NAUTOBOT_VER}"; \
                exit 1; \
            fi; \
            echo "Resolved NAUTOBOT_VER=${NAUTOBOT_VER} to installed Nautobot ${RESOLVED_NAUTOBOT_VER}"; \
        fi; \
        if ! poetry add --lock "nautobot@${RESOLVED_NAUTOBOT_VER}" --python "${PYTHON_VER}"; then \
            poetry add --lock "git+https://github.com/nautobot/nautobot.git#${NAUTOBOT_VER}" --python "${PYTHON_VER}"; \
        fi; \
    fi

# Install the nautobot project (lock file is already pinned to NAUTOBOT_VER)
RUN cd /source && \
    poetry install --no-interaction --no-ansi && \
    # Try to install the export plugin for Poetry v2, if it fails it's probably v1 so we can ignore it
    poetry self add poetry-plugin-export || true && \
    mkdir /tmp/dist && \
    poetry export --without-hashes -o /tmp/dist/requirements.txt

# Install dev/docs/linting/testing extras
RUN poetry install --with dev,docs,linting,testing

COPY development/nautobot_config.py ${NAUTOBOT_ROOT}/nautobot_config.py
# !!! USE CAUTION WHEN MODIFYING LINES ABOVE
