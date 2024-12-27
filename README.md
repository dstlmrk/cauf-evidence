# Ultihub

🥏 🇨🇿 👨‍💻 An app for ultimate frisbee national association and clubs to manage
memberships, fees, transfers, and other administrative tasks efficiently.

## Development

All commands what you need you can see in output of `poetry run poe help` command.

### Others

```bash
# Install pre-commit for better development experience
poetry run pre-commit install

# Prettier needs to be installed via npm (install node via brew)
npm install

# Install dependencies without app itself
poetry install --no-root

# Update lock file without updating dependencies
poetry lock --no-update

# Install new package
poetry add package

# Build new js/css bundles or watch for changes
npm run build
npm run watch
```

### Project start

```bash
# Migrate database
docker compose -f docker/compose.dev.yaml exec app python manage.py migrate

# Create superuser with empty email
docker compose -f docker/compose.dev.yaml exec app python manage.py createsuperuser --username admin

# Load initial data
docker compose -f docker/compose.dev.yaml exec app python manage.py loaddata initial_data
```

### Backup

```bash
./run-backup.sh mara 46.101.97.63
```

# API

This app offers API for a few cases. It is based on Django Rest Framework and uses token authentication.

## Authentication

All GET requests are public. For other requests, you need
to authenticate via token in the header `Authorization=Token <token>`.

For authentication, you need a user with a token. You can create him
in administration and generate token via `python manage.py drf_create_token <username>`.
Already created tokens are available at `/admin/authtoken/tokenproxy`.

## Endpoints

### /api/competitions

-   [GET] Returns all competitions. No filter is available at this moment.

### /api/clubs

-   [GET] Returns all clubs. No filter is available at this moment.

### /api/teams-at-tournament

-   [GET] Returns all teams at tournament with theirs roster. Parameter `tournament_id` is required.

### /api/team-at-tournament/\<int:pk>

-   [GET] Returns team at tournament with its roster.
-   [PATCH] Updates `final_placement` and `spirit_avg` fields.

### /api/competition-application/\<int:pk>

-   [GET] Returns competition application.
-   [PATCH] Updates `final_placement` field.
