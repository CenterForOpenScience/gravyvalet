![Center for Open Science Logo](https://mfr.osf.io/export?url=https://osf.io/download/24697/?direct=%26mode=render&format=2400x2400.jpeg)

# gravyvalet

gravyvalet fetches, serves, and holds small ladlefuls of precious bytes (in contrast to [waterbutler](), which fetches and serves whole streams of bytes but holds nothing)

currently, those bytes are shaped to support [osf addons](), whereby you can share controlled access to external accounts (e.g. online storage) with your collaborators on osf.

## Setting up GravyValet Locally

1. Start your PostgreSQL and Django containers with `docker compose up -d`.
2. Enter the Django container: `docker compose exec addon_service /bin/bash`.
3. Migrate the existing models: `python manage.py migrate`.
4. Visit [http://0.0.0.0:8004/](http://0.0.0.0:8004/).

## Running Tests

To run tests, use the following command:

```bash
python manage.py test
```

Development Tips

Optionally, but recommended: Set up pre-commit hooks that will run formatters and linters on staged files. Install pre-commit using:

```bash

pip install pre-commit
```

Then, run:

```bash

pre-commit install --allow-missing-config
```
Reporting Issues and Questions

If you encounter a bug, have a technical question, or want to request a feature, please don't hesitate to contact us 
at help@osf.io. While we may respond to questions through other channels, reaching out to us at help@osf.io ensures 
that your feedback goes to the right person promptly. If you're considering posting an issue on our GitHub issues page,
 we recommend sending it to help@osf.io instead.
