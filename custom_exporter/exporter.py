#!/usr/bin/env python3
"""
Prometheus exporter for custom health checks.
"""

import os
import sys
import json
import time
import socket
from textwrap import dedent
from urllib.parse import urlparse

import requests
import MySQLdb
from http.server import HTTPServer, BaseHTTPRequestHandler


DBNAME = os.environ['DBNAME']
DBUSER = os.environ['DBUSER']
DBPASS = os.environ['DBPASS']
REDISPASS = os.environ['REDISPASS']


class MetricsExporter:

    def __init__(self):
        self.metrics = {}

    def collect_metrics(self):
        """Run all checks and collect metrics."""
        self.check_rspamd_scoring()
        self.check_rspamd_milter()
        self.check_mysql_query()

    def check_rspamd_scoring(self):
        """Check rspamd scoring with a test message."""
        try:
            test_message = dedent("""\
                To: null@localhost
                From: monit@localhost

                Empty
            """)
            response = requests.post(
                'http://rspamd:11334/scan',
                data=test_message.encode('utf-8'),
                timeout=10,
                headers={'Content-Type': 'text/plain'}
            )

            if response.status_code == 200:
                result = response.json()
                score = result.get('default', {}).get('required_score', 0)
                # Expected score is 9999 (default reject threshold)
                if int(float(score)) == 9999:
                    self.metrics['rspamd_scoring_check'] = 1
                    self.metrics['rspamd_scoring_value'] = score
                else:
                    self.metrics['rspamd_scoring_check'] = 0
                    self.metrics['rspamd_scoring_value'] = score
            else:
                self.metrics['rspamd_scoring_check'] = 0
                self.metrics['rspamd_scoring_value'] = 0
        except Exception as e:
            print(f"Rspamd scoring check failed: {e}", file=sys.stderr)
            self.metrics['rspamd_scoring_check'] = 0
            self.metrics['rspamd_scoring_value'] = 0

    def check_rspamd_milter(self):
        """Check rspamd milter proxy is responding."""
        try:
            # Try to connect to milter port with short timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('rspamd', 9900))
            sock.close()

            # We expect connection to succeed (result == 0)
            # The original script checks for timeout (exit code 28),
            # we're checking if connection is accepted
            if result == 0:
                self.metrics['rspamd_milter_check'] = 1
            else:
                self.metrics['rspamd_milter_check'] = 0
        except Exception as e:
            print(f"Rspamd milter check failed: {e}", file=sys.stderr)
            self.metrics['rspamd_milter_check'] = 0

    def check_mysql_query(self):
        """Check MySQL with a test query."""
        try:
            # Connect via socket
            conn = MySQLdb.connect(
                unix_socket='/run/mysqld/mysqld.sock',
                user=DBUSER,
                passwd=DBPASS,
                db=DBNAME,
                connect_timeout=5
            )
            cursor = conn.cursor()

            # Test basic connection
            cursor.execute("SELECT 1")
            result = cursor.fetchone()

            if result and result[0] == 1:
                self.metrics['mysql_connection_check'] = 1
            else:
                self.metrics['mysql_connection_check'] = 0

            cursor.execute("SELECT COUNT(*) FROM information_schema.tables")
            result = cursor.fetchone()

            if result and result[0] > 0:
                self.metrics['mysql_query_check'] = 1
                self.metrics['mysql_table_count'] = result[0]
            else:
                self.metrics['mysql_query_check'] = 0
                self.metrics['mysql_table_count'] = 0

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"MySQL check failed: {e}", file=sys.stderr)
            self.metrics['mysql_connection_check'] = 0
            self.metrics['mysql_query_check'] = 0
            self.metrics['mysql_table_count'] = 0


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for /metrics endpoint."""

    def do_GET(self):
        if self.path == '/metrics':
            exporter = MetricsExporter()
            exporter.collect_metrics()

            # Generate Prometheus format output
            response = dedent(f"""\
                # HELP mail_rspamd_scoring_check Rspamd scoring check (1=pass, 0=fail)
                # TYPE mail_rspamd_scoring_check gauge
                mail_rspamd_scoring_check {exporter.metrics.get('rspamd_scoring_check', 0)}

                # HELP mail_rspamd_scoring_value Rspamd required score value
                # TYPE mail_rspamd_scoring_value gauge
                mail_rspamd_scoring_value {exporter.metrics.get('rspamd_scoring_value', 0)}

                # HELP mail_rspamd_milter_check Rspamd milter proxy check (1=pass, 0=fail)
                # TYPE mail_rspamd_milter_check gauge
                mail_rspamd_milter_check {exporter.metrics.get('rspamd_milter_check', 0)}

                # HELP mail_mysql_connection_check MySQL connection check (1=pass, 0=fail)
                # TYPE mail_mysql_connection_check gauge
                mail_mysql_connection_check {exporter.metrics.get('mysql_connection_check', 0)}

                # HELP mail_mysql_query_check MySQL query check (1=pass, 0=fail)
                # TYPE mail_mysql_query_check gauge
                mail_mysql_query_check {exporter.metrics.get('mysql_query_check', 0)}

                # HELP mail_mysql_table_count Number of tables in information_schema
                # TYPE mail_mysql_table_count gauge
                mail_mysql_table_count {exporter.metrics.get('mysql_table_count', 0)}
            """)

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK\n')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Override to reduce logging noise."""
        pass


def main():
    port = 9101
    server = HTTPServer(('0.0.0.0', port), MetricsHandler)
    print(f"Custom exporter listening on port {port}")
    server.serve_forever()


if __name__ == '__main__':
    main()
