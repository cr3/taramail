"""Prometheus exporter for custom health checks."""

import logging
import socket
from textwrap import dedent

from fastapi import (
    FastAPI,
    Response,
)
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Gauge,
    generate_latest,
)
from sqlalchemy import text

from taramail.db import DBSession
from taramail.deps import DbDep
from taramail.http import HTTPSession

logger = logging.getLogger("uvicorn")
app = FastAPI(title="Custom Exporter")

registry = CollectorRegistry()

rspamd_scoring_check = Gauge(
    "mail_rspamd_scoring_check",
    "Rspamd scoring check (1=pass, 0=fail)",
    registry=registry,
)
rspamd_scoring_value = Gauge(
    "mail_rspamd_scoring_value",
    "Rspamd required score value",
    registry=registry,
)
rspamd_milter_check = Gauge(
    "mail_rspamd_milter_check",
    "Rspamd milter proxy check (1=pass, 0=fail)",
    registry=registry,
)
mysql_connection_check = Gauge(
    "mail_mysql_connection_check",
    "MySQL connection check (1=pass, 0=fail)",
    registry=registry,
)
mysql_query_check = Gauge(
    "mail_mysql_query_check",
    "MySQL query check (1=pass, 0=fail)",
    registry=registry,
)
mysql_table_count = Gauge(
    "mail_mysql_table_count",
    "Number of tables in information_schema",
    registry=registry,
)


def check_rspamd_scoring(host: str, port: int = 11334) -> None:
    """Check rspamd scoring with a test message."""
    try:
        test_message = dedent("""\
            To: null@localhost
            From: monit@localhost

            Empty
        """)

        session = HTTPSession(f"http://{host}:{port}", timeout=10)
        response = session.post("/scan", data=test_message.encode("utf-8"))

        result = response.json()
        score = result.get("default", {}).get("required_score", 0)

        # Expected score is 9999 (default reject threshold)
        if int(float(score)) == 9999:
            rspamd_scoring_check.set(1)
            rspamd_scoring_value.set(score)
        else:
            rspamd_scoring_check.set(0)
            rspamd_scoring_value.set(score)
    except Exception:
        logger.exception("Error checking Rspamd scoring")
        rspamd_scoring_check.set(0)
        rspamd_scoring_value.set(0)


def check_rspamd_milter(host: str, port: int = 9900) -> None:
    """Check rspamd milter proxy is responding."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()

        rspamd_milter_check.set(1 if result == 0 else 0)
    except Exception:
        logger.exception("Error checking Rspamd milter")
        rspamd_milter_check.set(0)


def check_mysql_query(db: DBSession) -> None:
    """Check MySQL with a test query."""
    try:
        result = db.execute(text("SELECT 1")).scalar()
        mysql_connection_check.set(1 if result == 1 else 0)
    except Exception:
        mysql_connection_check.set(0)

    try:
        result = db.execute(text("SELECT COUNT(*) FROM information_schema.tables")).scalar()
        if result and result > 0:
            mysql_query_check.set(1)
            mysql_table_count.set(result)
        else:
            mysql_query_check.set(0)
            mysql_table_count.set(0)
    except Exception:
        logger.exception("Error checking MySQL")
        mysql_query_check.set(0)
        mysql_table_count.set(0)


@app.get("/check")
def check(db: DbDep, rspamd_host: str = "rspamd") -> Response:
    """Prometheus check endpoint."""
    check_rspamd_scoring(rspamd_host)
    check_rspamd_milter(rspamd_host)
    check_mysql_query(db)

    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
