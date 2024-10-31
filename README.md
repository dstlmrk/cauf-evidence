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

# Build new js/css bundles
npm run build
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
