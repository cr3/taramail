"""Integration tests for the rspamd service."""

from textwrap import dedent

from hamcrest import equal_to
from pytest_xdocker.retry import (
    calling,
    retry,
)

from taramail.http import HTTPSession


def test_rspamd_service(rspamd_service):
    """The score for emails from monit@localhost should be 9999."""
    email = dedent("""\
        To: null@localhost
        From: monit@localhost

        Empty
    """)
    http_session = HTTPSession(f"http://{rspamd_service.ip}:11333/")

    def scan(_http_session=http_session):
        response = _http_session.post("/scan", data=email)
        return response.json()["default"]["required_score"]

    retry(calling(scan)).until(equal_to(9999.0))
