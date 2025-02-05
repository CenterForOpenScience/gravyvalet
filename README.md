# 🥣 gravyvalet

`gravyvalet` fetches, serves, and holds small ladlefuls of precious bytes.

together with [waterbutler](https://waterbutler.readthedocs.io)
(which fetches and serves whole streams of bytes, but holds nothing),
gravyvalet provides an api to support "osf addons",
whereby you can share controlled access to online accounts
(e.g. cloud storage) with your collaborators on [osf](https://osf.io).

(NOTE: gravyvalet is still under active development and changes may happen suddenly,
tho current docs may or may not be available at https://addons.staging.osf.io/docs )

# how to...

## ...set up gravyvalet for local development with osf, using docker

0. have [osf running](https://github.com/CenterForOpenScience/osf.io/blob/develop/README-docker-compose.md) (with its `api` at `http://192.168.168.167:8000`)
1. Start your PostgreSQL and Django containers with `docker compose up -d`.
2. Enter the Django container: `docker compose exec gravyvalet /bin/bash`.
3. Migrate the existing models: `python manage.py migrate`.
4. Visit [http://0.0.0.0:8004/](http://0.0.0.0:8004/).

## ...run tests

To run tests, use the following command:

```bash
python manage.py test
```
(recommend adding `--failfast` when looking for immediate feedback)

## ...set up external services
start by creating an admin account with
[django's createsuperuser command](https://docs.djangoproject.com/en/4.2/ref/django-admin/#django-admin-createsuperuser):

```bash
python manage.py createsuperuser
```

then log in with that account at `localhost:8004/admin` to manage
external services (including oauth config) and to create other admin users


## ...configure a good environment
see `app/env.py` for details on all environment variables used.

when run without a `DEBUG` environment variable (note: do NOT run with `DEBUG` in production),
some additional checks are run on the environment:

- `GRAVYVALET_ENCRYPT_SECRET` is required -- ideally chosen by strong randomness,
  with maybe ~128 bits of entropy (e.g. 32 hex digits; 30 d20 rolls; 13 words of a 1000-word vocabulary)

## ...rotate encryption keys responsibly
don't let your secrets get stale! you can rotate the secret used to derive encryption keys
(as well as the parameters for key derivation -- see `app/env.py` for details)

1. update environment:
   - set `GRAVYVALET_ENCRYPT_SECRET` to a new, long, random string (...no commas, tho)
   - add the old secret to `GRAVYVALET_ENCRYPT_SECRET_PRIORS` (comma-separated list)
   - (optional) update key-derivation parameters with best-practices du jour
2. run `python manage.py rotate_encryption` to enqueue key-rotation tasks
   (on the `gravyvalet_tasks.CHILL` queue by default)
3. once that queue of tasks is complete, update environment again to remove the old secret from
   `GRAVYVALET_ENCRYPT_SECRET_PRIORS`

## ...enable pre-commit hooks
Optionally, but recommended: Set up pre-commit hooks that will run formatters and linters on staged files. Install pre-commit using:

```bash

pip install pre-commit
```

Then, run:

```bash

pre-commit install --allow-missing-config
```

## ...ask questions or report issues

If you encounter a bug, have a technical question, or want to request a feature, please don't hesitate to contact us 
at help@osf.io. While we may respond to questions through other channels, reaching out to us at help@osf.io ensures 
that your feedback goes to the right person promptly. If you're considering posting an issue on our GitHub issues page,
 we recommend sending it to help@osf.io instead.
avaialable
