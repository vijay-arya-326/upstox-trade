import webbrowser
from urllib.parse import parse_qs, urlparse
from threading import Event
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re
from pathlib import Path

from core.config.constants import AUTH_DIALOG_URL, GET_TOKEN_URL
from core.logging.fancy import fancy_print


def _get_login_settings():
    from core.config.settings import (
        UPSTOX_API_URL,
        UPSTOX_CLIENT_ID,
        UPSTOX_CLIENT_SECRET,
        UPSTOX_REDIRECT_URI,
        ENV_PATH,
    )
    return {
        "UPSTOX_API_URL": UPSTOX_API_URL,
        "UPSTOX_CLIENT_ID": UPSTOX_CLIENT_ID,
        "UPSTOX_CLIENT_SECRET": UPSTOX_CLIENT_SECRET,
        "UPSTOX_REDIRECT_URI": UPSTOX_REDIRECT_URI,
        "ENV_PATH": ENV_PATH,
    }


def _get_set_token_in_env():
    from core.auth.token_manager import set_token_in_env
    return set_token_in_env


def login():
    s = _get_login_settings()
    client_id: str = s["UPSTOX_CLIENT_ID"]
    client_secret: str = s["UPSTOX_CLIENT_SECRET"]
    redirect_url: str = s["UPSTOX_REDIRECT_URI"]
    env_path: Path = s["ENV_PATH"]

    url = s["UPSTOX_API_URL"]
    get_token_url = url + GET_TOKEN_URL
    auth_url = (
        f"{url}{AUTH_DIALOG_URL}"
        f"?response_type=code&client_id={client_id}&redirect_uri={redirect_url}"
    )
    webbrowser.open(auth_url)
    code = _capture_authorization_code(redirect_url)

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    json_payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_url,
        "grant_type": "authorization_code"
    }

    from requests import post
    from requests.exceptions import HTTPError

    try:
        get_token_from_code = post(get_token_url, headers=headers, data=json_payload)
        get_token_from_code.raise_for_status()
        response = get_token_from_code.json()
        _get_set_token_in_env()(response['access_token'], response['extended_token'], env_path)
        return True
    except HTTPError as http_err:
        fancy_print(f"HTTP error occurred: {http_err}", border_color="red")
        import json as json_mod
        fancy_print(json_mod.dumps(get_token_from_code.json(), indent=2))
    except Exception as e:
        fancy_print(e, border_color="red")
    return False


def _capture_authorization_code(redirect_uri: str, timeout: int = 180) -> str:
    parsed_redirect = urlparse(redirect_uri)
    expected_path = parsed_redirect.path or "/"
    port = parsed_redirect.port or (443 if parsed_redirect.scheme == "https" else 80)
    bind_address = _callback_bind_address(parsed_redirect.hostname)

    result: dict[str, str | None] = {"code": None, "error": None}
    done = Event()

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            request_path = urlparse(self.path).path or "/"
            if request_path != expected_path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(
                    f"Unexpected path {request_path}; expected {expected_path}".encode()
                )
                return

            query = parse_qs(urlparse(self.path).query)
            if "error" in query:
                result["error"] = query["error"][0]
            elif "code" in query:
                result["code"] = query["code"][0]

            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"Upstox login complete. You can close this tab and return to the bot."
            )
            done.set()

        def log_message(self, format, *args):
            return

    fancy_print(
        f"Listening for OAuth callback on http://{bind_address}:{port}{expected_path}",
        border_color="cyan",
    )

    server = HTTPServer((bind_address, port), CallbackHandler)
    server.timeout = 1

    def serve_requests():
        while not done.is_set():
            server.handle_request()

    thread = threading.Thread(target=serve_requests, daemon=True)
    thread.start()

    if not done.wait(timeout=timeout):
        server.server_close()
        raise (
            "Timed out waiting for Upstox login. Complete login in the browser within 3 minutes."
        )

    server.server_close()

    if result["error"]:
        raise (f"Upstox login error: {result['error']}")

    if not result["code"]:
        raise ("No authorization code received from Upstox redirect.")

    return str(result["code"])


def _callback_bind_address(hostname: str | None) -> str:
    if hostname in (None, "localhost", "127.0.0.1"):
        return "127.0.0.1"
    return hostname