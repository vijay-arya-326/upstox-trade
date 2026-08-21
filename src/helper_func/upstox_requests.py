import sys
from warnings import catch_warnings

from helper_func.config import (SANDBOX_UPSTOX_URL, LOADED_ENV,
    UPSTOX_URL, SANDBOX_ACCESS_TOKEN, UPSTOX_ACCESS_TOKEN)
from requests import get, post
from requests.exceptions import HTTPError
from helper_func.constants import LOGIN_URL, AUTH_DIALOG_URL, GET_TOKEN_URL, PLACE_ORDER_URL
import webbrowser
from urllib.parse import parse_qs, quote, urlparse
from helper_func.fancy_print import fancy_print, print_json
from threading import Event
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re
from pathlib import Path

def sandbox_token_active(forceProd:bool = False):
    if forceProd:
        url = UPSTOX_URL
        selected_token =  UPSTOX_ACCESS_TOKEN
        selected_env = "LIVE"
    else:
        url = SANDBOX_UPSTOX_URL
        selected_token = SANDBOX_ACCESS_TOKEN
        selected_env = "SANDBOX"

    final_url = url+ PLACE_ORDER_URL
    headers = {
        'accept': 'application/json',
        'Authorization': f"Bearer {selected_token}",
    }
    try:
        profile_response = post(final_url, headers=headers)
        profile_response.raise_for_status()
        print(profile_response.json())
        return True
    except HTTPError as http_err:
        if profile_response.status_code == 401:
           fancy_print(f"{selected_env} TOKEN EXPIRED!!! GENERATE NEW TOKEN AND PASTE IN ENV FILE", border_color="red")
        else:
            fancy_print(f"VALID {selected_env} TOKEN", border_color="blue")
            return True
        return False
    except Exception as e:
        print("FROM HEREE---2")
        fancy_print(str(e) + final_url, border_color="red")
        print_json(data=headers)
        return False

def login(client_id:str, client_secret:str, redirect_url: str, env_path: Path, forced_prod=True):
    url = UPSTOX_URL
    get_token_url = url+GET_TOKEN_URL
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
        "code":code,
        "client_id": client_id,
        "client_secret" : client_secret,
        "redirect_uri" : redirect_url,
        "grant_type" : "authorization_code"
    }

    try:
        get_token_from_code = post(get_token_url, headers=headers, data=json_payload )
        get_token_from_code.raise_for_status()
        # print(get_token_from_code.status_code)
        response  = get_token_from_code.json()
        set_token_in_env(response['access_token'], response['extended_token'], env_path)

    except HTTPError as http_err:
        fancy_print(f"HTTP error occurred: {http_err}", border_color="red")
        print_json(data= get_token_from_code.json(), indent=2)
    except Exception as e:
        fancy_print(e, border_color="red")



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

def set_token_in_env(access_token: str, extended_token: str, env_path:Path) -> None:
      os.environ["UPSTOX_ACCESS_TOKEN"] = access_token
      os.environ["UPSTOX_EXTENDED_TOKEN"] = extended_token
      _persist_access_token('UPSTOX_ACCESS_TOKEN', access_token, env_path)
      _persist_access_token('UPSTOX_EXTENDED_TOKEN', extended_token, env_path)

def _persist_access_token(key: str, token: str, env_path: Path) -> None:
    content = env_path.read_text(encoding="utf-8")
    line = f"{key}={token}"

    if re.search(rf"^{re.escape(key)}=", content, flags=re.MULTILINE):
        content = re.sub(
            rf"^{re.escape(key)}=.*$",
            line,
            content,
            flags=re.MULTILINE,
        )
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += line + "\n"

    env_path.write_text(content, encoding="utf-8")
    os.environ["UPSTOX_ACCESS_TOKEN"] = token