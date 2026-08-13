from logging.config import fileConfig
import sys
import os

from sqlalchemy import engine_from_config
from sqlalchemy import inspect, text
from sqlalchemy import pool

from alembic import context
from alembic.script import ScriptDirectory

# Add the parent directory to sys.path to import fastapi_app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi_app.app.db.models import Base
from fastapi_app.app.core.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url from environment
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata


def _is_fresh_head_upgrade(connection) -> bool:
    """Return true only for ``alembic upgrade head`` on an empty database.

    RankCare's first historical Alembic revision was generated as a bridge
    from an existing Prisma-managed schema.  It cannot bootstrap an empty
    database.  Existing/versioned databases must continue through that
    history unchanged; only a genuinely empty database uses the current
    schema baseline below.
    """
    cmd_opts = getattr(config, "cmd_opts", None)
    command = getattr(cmd_opts, "cmd", None)
    command_name = getattr(command[0], "__name__", None) if command else None
    destination = getattr(cmd_opts, "revision", None)
    if command_name != "upgrade" or destination != "head":
        return False

    application_tables = set(inspect(connection).get_table_names()) - {"alembic_version"}
    return not application_tables


def _bootstrap_current_head(connection) -> None:
    """Create the current model baseline and stamp the sole head."""
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"Fresh bootstrap requires exactly one Alembic head; found {heads}")

    target_metadata.create_all(bind=connection)
    connection.execute(text(
        "CREATE TABLE IF NOT EXISTS alembic_version "
        "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
    ))
    connection.execute(text("DELETE FROM alembic_version"))
    connection.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
        {"revision": heads[0]},
    )

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        fresh_head_upgrade = _is_fresh_head_upgrade(connection)
        if fresh_head_upgrade:
            _bootstrap_current_head(connection)
            connection.commit()
            return
        if connection.in_transaction():
            # Inspector calls use SQLAlchemy autobegin.  End that read-only
            # transaction so Alembic owns and commits the migration transaction.
            connection.rollback()

        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
