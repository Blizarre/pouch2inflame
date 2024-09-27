import json
import smtplib
from time import sleep
import tempfile
import time
import tomllib
from argparse import ArgumentParser, Namespace
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import format_datetime
from subprocess import PIPE, Popen
from typing import IO, Any, Dict, List
from urllib import request
from urllib.parse import quote


class UnexpectedPocketReponseException(BaseException):
    pass


@dataclass
class SMTPConfig:
    server: str
    port: int
    user: str
    password: str
    email_from: str


@dataclass
class UserConfig:
    destination_email: str
    username: str
    access_token: str


class Config:
    def __init__(self, file_name):
        with open(file_name, "rb") as config_fd:
            self._config = tomllib.load(config_fd)

    @property
    def config(self) -> Dict[str, Any]:
        # It's not really nice but we can't easily enforce
        # read-only values in Pythons
        return deepcopy(self._config)

    @property
    def users(self) -> List[UserConfig]:
        return [
            UserConfig(username=username, **config)
            for username, config in self._config.get("accounts", []).items()
        ]

    @property
    def smtp(self) -> SMTPConfig:
        return SMTPConfig(**self.config["smtp"])

    @property
    def consumer_key(self) -> str:
        return self._config["consumer_key"]

    @property
    def redirect_uri(self) -> str:
        return self._config.get("redirect_uri", "https://www.getpocket.com")

    @property
    def sleep_between_articles(self) -> float:
        return self._config.get("sleep_between_articles", 10.0)


def http_post_json(url: str, data: Any) -> Any:
    """reimplementing the `requests` library. It's not worth
    adding a dependency for that. urllib is used instead"""
    req = request.Request(url, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Accept", "application/json")
    data_bytes = json.dumps(data).encode()

    with request.urlopen(req, data=data_bytes) as response:
        return json.loads(response.read())


def run_in_docker(command: List[str], **kwargs) -> Popen[str]:
    return Popen(
        ["sudo", "docker", "run", "-i", "converter:latest"] + command, **kwargs
    )


def send_arbitrary_file(config: Config, args: Namespace):
    for user in config.users:
        if user.username == args.username:
            with open(args.filename, "rb") as epub_fd:
                send_epub_by_email(user, config.smtp, epub_fd)


def send_epub_by_email(user: UserConfig, smtp: SMTPConfig, epub_fd: IO):
    content = epub_fd.read()
    print(f"  Sending file ({len(content)} bytes) to {user.destination_email}")

    message = EmailMessage()
    message["From"] = smtp.email_from
    message["To"] = user.destination_email
    message["Subject"] = "epub file for kindle"
    message["Date"] = format_datetime(datetime.now())
    message.set_content("Kindle, please import the epub file attached to that email")
    message.add_attachment(
        content,
        maintype="application",
        subtype="epub+zip",
        filename=f"{datetime.now().date()}.epub",
    )

    with smtplib.SMTP_SSL(smtp.server, smtp.port) as service:
        service.login(smtp.user, smtp.password)
        service.send_message(
            message,
            smtp.email_from,
            user.destination_email,
        )


def get_list_of_articles(consumer_key: str, access_token: str) -> List[Dict[str, Any]]:
    response = http_post_json(
        "https://getpocket.com/v3/get",
        {
            "consumer_key": consumer_key,
            "access_token": access_token,
            "contentType": "article",
        },
    )
    # The API return either an empty list or a dict of values. The rules there aren't
    # really clear.
    articles = response["list"]
    if isinstance(articles, type({})):
        return articles.values()  # type: ignore
    if isinstance(articles, type([])):
        return articles

    raise UnexpectedPocketReponseException(
        f"Unknown return type from the get api. Value is f{articles}"
    )


def process_and_send_emails(config: Config, _args: Namespace):
    for user in config.users:
        print(f"Processing pocket entries for '{user.username}'")
        for article in get_list_of_articles(config.consumer_key, user.access_token):
            title = article["resolved_title"]
            url = article["resolved_url"]
            item_id = article["item_id"]
            print(f"  Processing article '{title}'")
            with tempfile.NamedTemporaryFile(suffix=".epub") as tmpfile:
                extractor = run_in_docker(["extractor", url], stdout=PIPE)
                epub_converter = run_in_docker(
                    [
                        "pandoc",
                        "-f",
                        "html",
                        "-t",
                        "epub",
                        "-o",
                        "-",
                        "--metadata",
                        f"title={title}",
                    ],
                    stdin=extractor.stdout,
                    stdout=tmpfile,
                )
                if extractor.wait() != 0:
                    print(
                        "Error during content extraction (readibility.js). Please look at the logs"
                    )
                    continue
                if epub_converter.wait() != 0:
                    print(
                        "Error during html -> epub conversion (pandoc). Please look at the logs"
                    )
                    continue

                tmpfile.seek(0)  # Rewind to be able to read the content
                send_epub_by_email(user, config.smtp, tmpfile)
                http_post_json(
                    "https://getpocket.com/v3/send",
                    {
                        "consumer_key": config.consumer_key,
                        "access_token": user.access_token,
                        "actions": [
                            {
                                "action": "archive",
                                "item_id": item_id,
                                "time": int(time.time()),
                            }
                        ],
                    },
                )
                sleep(config.sleep_between_articles)


def get_token(config: Config, _args: Namespace):
    oauth_request = http_post_json(
        "https://getpocket.com/v3/oauth/request",
        {
            "consumer_key": config.consumer_key,
            "redirect_uri": config.redirect_uri,
        },
    )
    code = oauth_request["code"]
    print(f"Received code {code}, please login at:")
    print(
        f"https://getpocket.com/auth/authorize?request_token={code}&"
        + f"redirect_uri={quote(config.redirect_uri)}"
    )

    print("\nPress ENTER after the redirect")
    _dummy = input()

    auth_request = http_post_json(
        "https://getpocket.com/v3/oauth/authorize",
        {
            "consumer_key": config.consumer_key,
            "code": code,
        },
    )
    print(f"Authentication successful, credentials:\n{auth_request}")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--config-file", default="config.toml")
    subparser = parser.add_subparsers()

    get_token_parser = subparser.add_parser(
        "get_token", help="Helper to get a new access token"
    )
    get_token_parser.set_defaults(func=get_token)

    send_epub_file_parser = subparser.add_parser(
        "send_epub_file", help="Helper to test the file sending pipeline"
    )
    send_epub_file_parser.add_argument("username")
    send_epub_file_parser.add_argument("filename")
    send_epub_file_parser.set_defaults(func=send_arbitrary_file)

    process_and_send = subparser.add_parser(
        "process_and_send", help="Fetch the pocket entries and send the epubs"
    )
    process_and_send.set_defaults(func=process_and_send_emails)

    app_args = parser.parse_args()
    app_config = Config(app_args.config_file)

    if "func" not in app_args:
        print("Missing verb, rerun with --help for more information")
        parser.print_help()
        parser.exit(1)

    app_args.func(app_config, app_args)
