![Center for Open Science Logo](https://mfr.osf.io/export?url=https://osf.io/download/24697/?direct=%26mode=render&format=2400x2400.jpeg)

# OSF Addon Service (GravyValet)

Welcome to the Open Science Framework's base server for addon integration with our RESTful API (osf.io). This server acts as a gateway between the OSF and external APIs. Authenticated users or machines can access various resources through common file storage and citation management APIs via the OSF. Institutional members can also add their own integrations, tailoring addon usage to their specific communities.

## Setting up GravyValet Locally

1. Start your PostgreSQL and Django containers with `docker compose up -d`.
2. Enter the Django container: `docker compose exec addon_service /bin/bash`.
3. Make migrations `python manage.py makemigrations`.
4. Migrate the existing models: `python manage.py migrate`.
5. Visit [http://0.0.0.0:8004/](http://0.0.0.0:8004/).

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
