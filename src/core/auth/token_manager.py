import os
import re
from pathlib import Path
from requests import post
from requests.exceptions import HTTPError

from core.config.constants import PLACE_ORDER_URL, SANDBOX_ENV_NAME
from core.logging.fancy import fancy_print, print_json


def _get_auth_settings():
    from core.config.settings import (
        SANDBOX_UPSTOX_URL,
        LOADED_ENV,
        UPSTOX_API_URL,
        SANDBOX_ACCESS_TOKEN,
        UPSTOX_ACCESS_TOKEN,
    )
    return {
        "SANDBOX_UPSTOX_URL": SANDBOX_UPSTOX_URL,
        "LOADED_ENV": LOADED_ENV,
        "UPSTOX_API_URL": UPSTOX_API_URL,
        "SANDBOX_ACCESS_TOKEN": SANDBOX_ACCESS_TOKEN,
        "UPSTOX_ACCESS_TOKEN": UPSTOX_ACCESS_TOKEN,
    }


def _get_login():
    from core.auth.login import login
    return login


def sandbox_token_active(forceProd: bool = False):
    s = _get_auth_settings()
    if forceProd:
        url = s["UPSTOX_API_URL"]
        selected_token = s["UPSTOX_ACCESS_TOKEN"]
        selected_env = "LIVE"
    else:
        url = s["SANDBOX_UPSTOX_URL"]
        selected_token = s["SANDBOX_ACCESS_TOKEN"]
        selected_env = "SANDBOX"

    final_url = url + PLACE_ORDER_URL
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
            fancy_print(f"{selected_env} TOKEN EXPIRED!!! GENERATE NEW TOKEN AND PASTE IN ENV FILE", border_color="red3", title="HTTP Error")
        else:
            fancy_print(f"VALID {selected_env} TOKEN", border_color="blue")
            return True
        return False
    except Exception as e:
        fancy_print(str(e) + final_url, border_color="red")
        print_json(data=headers)
        return False


def check_user_auth() -> None:
    active_token = sandbox_token_active(forceProd=True)
    if active_token == False:
        _get_login()()


def validate_sandbox_token():
    return sandbox_token_active()


def set_token_in_env(access_token: str, extended_token: str, env_path: Path) -> None:
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