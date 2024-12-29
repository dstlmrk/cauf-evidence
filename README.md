# Ultihub

🥏 🇨🇿 👨‍💻 An app for ultimate frisbee national association and clubs to manage
memberships, fees, transfers, and other administrative tasks efficiently.

## Overview

Below is a high-level overview of the project's components:

-   **Containerized Architecture**: The entire application is structured as Docker images managed with `docker-compose`.
-   **Backend**: Developed with the latest versions of Python and Django.
-   **Database**: PostgreSQL serves as the database, ~with automated backups to S3 for data security and redundancy~.
-   **Frontend**:
    -   Primarily server-rendered.
    -   Dynamic elements implemented using Alpine.js and HTMX.
    -   Bootstrap is used for responsive and consistent styling.
-   **Authentication**: User authentication is handled exclusively via Google Sign-In for simplicity and security.
-   **Administration**: Django Admin is utilized for administrative tasks, such as managing data or configurations.
-   **Error and Performance Monitoring**:
    -   Errors are captured by Sentry.
    -   Performance and application monitoring data are sent to Datadog.
-   **Deployment and Hosting**:
    -   The application is hosted on a Digital Ocean VPS.
    -   Automatic HTTPS certificates are managed via `nginxproxy/acme-companion`.
    -   CI/CD workflows on GitHub automate builds and deployments.
-   **Asynchronous Operations**: Redis is used as the message queue for handling asynchronous tasks.
-   **Invoice Management**: Integration with Fakturoid is used to handle invoicing and financial management.

### Applications

-   **Api**: Manage API endpoints and permissions for them.
-   **Clubs**: Manage club information, teams and club notifications.
-   **Competitions**: Manage competitions (seasons, divisions, age limits) and applications.
-   **Core**: Includes common logic and utilities used across the project.
-   **Finance**: Manage invoices and Fakturoid integration.
-   **Members**: Manage member information, coach licenses, and transfers.
-   **Tournaments**: Manage tournaments, and teams and members (rosters) at tournaments.
-   **Users**: Manage agents in the app.

### Production

The app is hosted on Digital Ocean VPS on `46.101.97.63` and it is accessible via `https://evidence.frisbee.cz/`.

#### Backup

Temporarily, backups are managed manually. To create a backup,
run the following command (it requires access to the server):

```bash
./run-backup.sh mara 46.101.97.63
```

The backup is stored in the `backups` directory on your local machine.

## API

This app offers API for a few cases. It is based on Django Rest Framework and uses token authentication.

### Authentication

All GET requests are public. For other requests, you need
to authenticate via token in the header `Authorization=Token <token>`.

For authentication, you need a user with a token. You can create him
in administration and generate token via `python manage.py drf_create_token <username>`.
Already created tokens are available at `/admin/authtoken/tokenproxy`.

### Endpoints

#### /api/competitions

-   `GET` Returns all competitions. No filter is available at this moment.

#### /api/clubs

-   `GET` Returns all clubs. No filter is available at this moment.

#### /api/teams-at-tournament

-   `GET` Returns all teams at tournament with theirs roster. Parameter `tournament_id` is required.

#### /api/team-at-tournament/\<int:pk>

-   `GET` Returns team at tournament with its roster.
-   `PATCH` Updates `final_placement` and `spirit_avg` fields.

#### /api/competition-application/\<int:pk>

-   `GET` Returns competition application.
-   `PATCH` Updates `final_placement` field.

## Database schema

This image includes all business related tables and their relations.

![db_schema](https://github.com/dstlmrk/cauf-evidence/blob/main/db_schema.png)

It's generated by `django-extensions` package. For re-generation,
you must install `graphviz` locally and follow these steps:

1. Run docker-compose with the app container
2. ```bash
   docker compose -f docker/compose.dev.yaml exec app python manage.py graph_models clubs competitions finance members tournaments users -X AuditModel,ContentType --hide-edge-labels -o models.dot
   ```
3. ```bash
   docker cp app:/app/ultihub/models.dot
   ```
4. ```bash
   dot -Tpng models.dot -o models.png
   ```

For more informations visit [django-extensions](https://django-extensions.readthedocs.io/en/latest/graph_models.html) documentation.

## Local development

For fresh start, follow these steps:

```bash
# Pull and buiforld images
docker compose -f docker/compose.dev.yaml build

# Run containers
docker compose -f docker/compose.dev.yaml up -d

# Migrate database
docker compose -f docker/compose.dev.yaml exec app python manage.py migrate

# Create superuser with empty email
docker compose -f docker/compose.dev.yaml exec app python manage.py createsuperuser --username admin

# Load initial data
docker compose -f docker/compose.dev.yaml exec app python manage.py loaddata initial_data
```

App is prepared with initial data, and you can access it on `localhost:8000`.

For another useful commands what you could need you need to install `poetry`.
Then check all possible options in output of `poetry run poe help` command.

For better development experience, you need install pre-commit hooks and prettier:

```bash
# Install pre-commit for better development experience
poetry run pre-commit install

# Prettier needs to be installed via npm (install node via brew)
npm install
```

### Don't forget

```bash
# Install dependencies without app itself
poetry install --no-root

# Update lock file without updating dependencies
poetry lock --no-update

# Install new package
poetry add package

# Build new js/css bundles
npm run build

# Watch for changes
npm run watch
```
