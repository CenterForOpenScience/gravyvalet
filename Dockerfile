# Use the official Python image AS the base image
FROM python:3.13 AS gv-base

# System Dependencies:
RUN apt-get update && apt-get install -y libpq-dev libxml2-dev libxslt-dev

COPY pyproject.toml /code/
COPY poetry.lock /code/

WORKDIR /code
ENV PATH="$PATH:/root/.local/bin"
# END gv-base

# BEGIN gv-runtime-base
FROM python:3.13-slim AS gv-runtime-base

# System Dependencies:
RUN apt-get update && apt-get install -y libpq-dev libxml2-dev libxslt-dev

COPY pyproject.toml /code/
COPY poetry.lock /code/

WORKDIR /code
ENV PATH="$PATH:/root/.local/bin"
# END gv-runtime-base

# BEGIN dev-deps
FROM gv-base AS dev

# install dev and non-dev dependencies:
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.8.3
RUN poetry config virtualenvs.create false
RUN poetry install --without release

COPY . /code/

# Start the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8004"]
# END dev

# BEGIN gv-docs
FROM dev AS gv-docs
RUN poetry run python -m gravyvalet_code_docs.build
# END gv-docs

# BEGIN dist-deps
FROM gv-base AS dist-deps
# install non-dev and release-only dependencies:
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.8.3
RUN python -m venv .venv
RUN poetry install --without dev
# ENF dist-deps


# BEGIN dist
FROM gv-runtime-base AS dist
COPY --from=dist-deps /code/.venv/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY . /code/
# copy auto-generated static docs (without the dev dependencies that built them)
COPY --from=gv-docs /code/addon_service/static/gravyvalet_code_docs/ /code/addon_service/static/gravyvalet_code_docs/
RUN python manage.py collectstatic --noinput
# note: no CMD in dist -- depends on deployment
# END dist
