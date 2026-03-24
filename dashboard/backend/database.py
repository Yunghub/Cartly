import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _mysql_url(database: str | None) -> URL:
    return URL.create(
        "mysql+pymysql",
        username=os.getenv("MYSQL_USER", "admin"),
        password=os.getenv("MYSQL_PASSWORD", "cartlydatabase"),
        host=os.getenv(
            "MYSQL_HOST", "cartly-database.czoceemm8dli.eu-west-2.rds.amazonaws.com"
        ),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        database=database,
        query={"charset": "utf8mb4"},
    )


DATABASE_NAME = os.getenv("MYSQL_DATABASE", "mysql")
DATABASE_URL = os.getenv("DATABASE_URL") or _mysql_url(DATABASE_NAME).render_as_string(
    hide_password=False
)


def _bootstrap_mysql_database() -> None:
    if not DATABASE_URL.startswith("mysql+pymysql://"):
        return

    if os.getenv("MYSQL_BOOTSTRAP_DB", "0") != "1":
        return

    admin_database = os.getenv("MYSQL_ADMIN_DATABASE", "mysql")
    bootstrap_engine = create_engine(
        _mysql_url(admin_database),
        pool_pre_ping=True,
    )
    try:
        with bootstrap_engine.begin() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{DATABASE_NAME}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
    finally:
        bootstrap_engine.dispose()


_bootstrap_mysql_database()

engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
