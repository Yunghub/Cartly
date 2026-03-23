import os
import socket
import subprocess
import time

import pymysql
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_DB_HOST = "cartly-database.czoceemm8dli.eu-west-2.rds.amazonaws.com"
_DB_USER = "admin"
_DB_PASS = "cartlydatabase"
_DB_NAME = "trolley"

_SSH_HOST = "16.60.248.46"
_SSH_USER = "ubuntu"
_SSH_KEY = "C:/Users/mryun/Downloads/cartly3.pem"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SQLITE_PATH = os.path.join(_BASE_DIR, "trolley.db")


def _reachable(host, port=3306, timeout=2):
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def _can_use_ssh_key(path):
    return os.path.exists(path)


def _mysql_url(host, port):
    return (
        f"mysql+pymysql://{_DB_USER}:{_DB_PASS}"
        f"@{host}:{port}/{_DB_NAME}"
    )


def _try_mysql_connection(host, port):
    conn = pymysql.connect(host=host, port=port, user=_DB_USER, password=_DB_PASS, connect_timeout=3)
    try:
        conn.cursor().execute(f"CREATE DATABASE IF NOT EXISTS `{_DB_NAME}`")
    finally:
        conn.close()


_tunnel_proc = None
DATABASE_URL = None

# Prefer direct RDS when available.
if _reachable(_DB_HOST):
    try:
        _try_mysql_connection(_DB_HOST, 3306)
        DATABASE_URL = _mysql_url(_DB_HOST, 3306)
        print(f"[DB] Using direct MySQL connection to {_DB_HOST}:3306")
    except Exception as exc:
        print(f"[DB] Direct MySQL unavailable: {exc}")

# If direct access is unavailable, try the SSH tunnel.
if DATABASE_URL is None and _can_use_ssh_key(_SSH_KEY):
    try:
        _tunnel_proc = subprocess.Popen(
            [
                "ssh", "-N",
                "-L", f"3307:{_DB_HOST}:3306",
                "-i", _SSH_KEY,
                "-o", "StrictHostKeyChecking=no",
                "-o", "ExitOnForwardFailure=yes",
                "-o", "ServerAliveInterval=30",
                f"{_SSH_USER}@{_SSH_HOST}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        _try_mysql_connection("127.0.0.1", 3307)
        DATABASE_URL = _mysql_url("127.0.0.1", 3307)
        print(f"[DB] SSH tunnel open: 127.0.0.1:3307 -> {_DB_HOST}:3306 via {_SSH_HOST}")
    except Exception as exc:
        if _tunnel_proc is not None:
            _tunnel_proc.terminate()
            _tunnel_proc = None
        print(f"[DB] SSH tunnel unavailable, falling back to SQLite: {exc}")
elif DATABASE_URL is None:
    print(f"[DB] SSH key not found at {_SSH_KEY}, falling back to SQLite")

# Final fallback for local development.
if DATABASE_URL is None:
    DATABASE_URL = f"sqlite:///{_SQLITE_PATH}"
    print(f"[DB] Using local SQLite database at {_SQLITE_PATH}")


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:///") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
