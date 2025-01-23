"""Integration tests for the MySQL service."""

import os
from subprocess import CalledProcessError

from pytest_xdocker.docker import docker
from pytest_xdocker.retry import retry


def test_mysql(mysql_client):
    """The MySQL service should allow connection from DBUSER."""
    command = docker.exec_(mysql_client.name).with_command(
        "mysql",
        "--execute=SELECT VERSION();",
        f"--user={os.environ['DBUSER']}",
        f"--password={os.environ['DBPASS']}",
        os.environ["DBNAME"],
    )
    result = retry(command.execute).catching(CalledProcessError)
    assert "MariaDB" in result
