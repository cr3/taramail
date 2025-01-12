"""Integration tests for the dyndns service."""

import json
import time

import requests
from pytest_xdocker.docker import docker


def test_dyndns(tmp_path):
    """The dyndns service should do nothing when records are up to date."""
    response = requests.get("https://api.ipify.org", timeout=1)
    ip = response.text
    settings = tmp_path / "settings.txt"
    settings.write_text(
        json.dumps({
            "test": {
                "ip": {
                    "IPv4": ip,
                },
                "protocols": ["IPv4"],
                "last_success": time.time(),
                "provider_name": "test",
                "url_api": "http://localhost:8000",
            },
        }),
        encoding="ascii",
    )
    output = (
        docker.compose()
        .run("dyndns")
        .with_build()
        .with_remove()
        .with_volume(
            settings,
            "/test-settings.txt",
        )
        .with_command(
            "/usr/local/bin/domain-connect-dyndns",
            "update",
            "--all",
            "--config",
            "/test-settings.txt",
        )
        .execute(capture_output=True, universal_newlines=True)
    )
    assert "All records up to date" in output.stdout
