# Graph MSR Tool - Backend

Backend for the Graph MSR Tool that manages the drill jobs and stores data for the frontend.

Serves 3 functions:

- Stores the configuration files that the user has saved
- Executes drill jobs by adding them onto the RabbitMQ message queue Remote procedure call.
- Stores the status of drill jobs
- Stores saved queries

## Technologies

Poetry - dependency mabnagement
FastAPI
SQLModel - SqlAlchemy and PyDantic models
Alembic - Manages dataabse migrations
AIO Pika - Asyncronous RabbitMQ

### Adding a dependency

```terminal
poetry add <dependency>
```

## Creating a Database Migration

After making changes to the database models, the changes must be migrated to the database. This is alembics job. It acts as version control for the database structure.

1. Activate a bash terminal inside the backend docker container:

```bash
docker compose exec -it backend bash
```

2. Inside the container bash terminal create the migration:

```bash
cd backend
alembic revision --autogenerate -m "<message>"
```

> Ensure that you change `<message>`.

3. Then apply the migrations

```bash
alembic upgrade head
```
