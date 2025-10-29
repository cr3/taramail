"""Command-line interface."""

import json
import os
import sys
from argparse import (
    ArgumentParser,
    FileType,
    RawDescriptionHelpFormatter,
)
from collections import defaultdict
from textwrap import dedent

from lookuper import lookup
from more_itertools import bucket, only
from requests import HTTPError, RequestException

from taramail.http import HTTPSession

DEFAULT_API_URL = "https://mail.taram.ca/"


def get_arg_type(arg, default=str):
    """OpenAPI data type to arg type."""
    return {
        "boolean": bool,
        "integer": int,
        "number": float,
        "string": str,
    }.get(arg, default)


def get_openapi_schema(session):
    """Get and parse the OpenAPI schema from the API."""
    response = session.get("/api/openapi.json", verify=False)
    return response.json()


def call_api(session, method, path, args, keys):
    """Make an API request with query parameters and request body."""
    values = bucket(args.items(), lambda a: keys.get(a[0]))
    values = defaultdict(dict, {k: dict(values[k]) for k in values})

    headers = {"Content-Type": "application/json"} if values["body"] else {}
    response = session.request(
        method.upper(),
        path.format(**values["path"]),
        params=values["query"],
        json=values["body"],
        headers=headers,
        verify=not args.get("no_verify", False),
    )

    return response.json()


def make_args_parser():
    epilog = dedent(f"""\
    environments:
      TARAMAIL_API_URL     URL of the API (default: {DEFAULT_API_URL})
    """)
    args_parser = ArgumentParser(
        epilog=epilog,
        formatter_class=RawDescriptionHelpFormatter,
    )
    args_parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Do not verify the SSL certificate.",
    )
    args_parser.add_argument(
        "--output",
        type=FileType("w"),
        default=sys.stdout,
        help="output file (default: stdout)",
    )

    return args_parser


def add_command_args(args_parser, schema):
    command = args_parser.add_subparsers(
        dest="command",
    )

    # Add schema paths.
    for path, methods in schema.get("paths", {}).items():
        for method, details in methods.items():
            default_name = f"{method}_{path.strip('/').replace('/', '_')}"
            command_name = details.get("operationId", default_name)
            command_parser = command.add_parser(
                command_name,
                help=details.get("summary", "No summary available"),
            )

            # Add query/path parameters.
            keys = {}
            for param in details.get("parameters", []):
                keys[param["name"]] = param["in"]
                required = param.get("required", False)
                param_name = param["name"] if required else f"--{param['name']}"
                param_type = get_arg_type(param["schema"].get("type"))
                command_parser.add_argument(
                    param_name,
                    type=param_type,
                    help=param["schema"].get("title"),
                )

            # Add requestBody properties.
            if content_schema := only(lookup(details, "requestBody", "content", "application/json", "schema")):
                if ref := content_schema.get("$ref"):
                    content_schema = only(lookup(schema, *ref.split("/")[1:]))

                for prop_name, prop_details in content_schema.get("properties", {}).items():
                    keys[prop_name] = "body"
                    required = prop_name in content_schema.get("required", [])
                    arg_name = prop_name if required else f"--{prop_name}"
                    arg_default = prop_details.get("default")
                    arg_type = get_arg_type(prop_details.get("type"))
                    kwargs = {}
                    if arg_type is bool:
                        if arg_default:
                            arg_name = arg_name.replace(prop_name, f"no_{prop_name}")
                            kwargs["action"] = "store_false"
                        else:
                            kwargs["action"] = "store_true"
                    else:
                        kwargs["type"] = arg_type

                    if not required:
                        arg_name = arg_name.replace("_", "-")
                        kwargs["dest"] = prop_name

                    command_parser.add_argument(
                        arg_name,
                        default=arg_default,
                        help=prop_details.get("title"),
                        **kwargs,
                    )

            command_parser.set_defaults(
                func=lambda session, args, m=method, p=path, keys=keys: call_api(session, m, p, args, keys),
            )

    return args_parser


def main(argv=None):
    """Entry point to the taramail command-line interface."""
    api_url = os.getenv("TARAMAIL_API_URL", DEFAULT_API_URL)

    parser = make_args_parser()
    session = HTTPSession.with_origin(api_url)
    try:
        schema = get_openapi_schema(session)
    except RequestException as e:
        parser.error(e)

    parser = add_command_args(parser, schema)
    args = parser.parse_args(argv)
    try:
        data = args.func(session, vars(args))
    except HTTPError as e:
        parser.error(e)

    output = json.dumps(data, indent=2)
    args.output.write(output)
