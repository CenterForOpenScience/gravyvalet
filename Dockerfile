# Use the official Python image AS the base image
FROM python:3.12 AS gv-base

# System Dependencies:
RUN apt-get update && apt-get install -y libpq-dev

COPY pyproject.toml /code/
COPY poetry.lock /code/

WORKDIR /code
ENV PATH="$PATH:/root/.local/bin"
# END gv-base

# BEGIN gv-runtime-base
FROM python:3.12-slim AS gv-runtime-base

# System Dependencies:
RUN apt-get update && apt-get install -y libpq-dev

COPY pyproject.toml /code/
COPY poetry.lock /code/

WORKDIR /code
ENV PATH="$PATH:/root/.local/bin"
# END gv-runtime-base

# BEGIN gv-dev-deps
FROM gv-base AS gv-dev-deps

# install dev and non-dev dependencies:
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.8.3
RUN python -m venv .venv
RUN poetry install --without release
# END gv-dev-deps

# BEGIN gv-dev
FROM gv-runtime-base AS gv-dev

COPY --from=gv-dev-deps /code/.venv/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

COPY . /code/

# Start the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8004"]
# END gv-dev

# BEGIN gv-docs
FROM gv-dev AS gv-docs
RUN python -m gravyvalet_code_docs.build
# END gv-docs

# BEGIN gv-deploy-deps
FROM gv-base AS gv-deploy-deps
# install non-dev and release-only dependencies:
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.8.3
RUN python -m venv .venv
RUN poetry install --without dev
# ENF gv-deploy-deps


# BEGIN gv-deploy
FROM gv-runtime-base AS gv-deploy
COPY --from=gv-deploy-deps /code/.venv/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY . /code/
# copy auto-generated static docs (without the dev dependencies that built them)
COPY --from=gv-docs /code/addon_service/static/gravyvalet_code_docs/ /code/addon_service/static/gravyvalet_code_docs/
RUN python manage.py collectstatic --noinput
# note: no CMD in gv-deploy -- depends on deployment
# END gv-deploy
