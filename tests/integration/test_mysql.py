"""Integration tests for the MySQL service."""

from subprocess import CalledProcessError

from pytest_xdocker.docker import docker
from pytest_xdocker.retry import retry


def test_mysql(mysql_client):
    """The MySQL service should allow connection from DBUSER."""
    env = mysql_client.env
    command = docker.exec_(mysql_client.name).with_command(
        "mysql",
        "--execute=SELECT VERSION();",
        f"--user={env['MYSQL_USER']}",
        f"--password={env['MYSQL_PASSWORD']}",
        env["MYSQL_DATABASE"],
    )
    result = retry(command.execute).catching(CalledProcessError)
    assert "MariaDB" in result
