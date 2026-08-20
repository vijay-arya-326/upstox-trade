from helper_func.config import  (
    APPNAME,
    UPSTOX_CLIENT_ID,
    UPSTOX_CLIENT_SECRET,
    UPSTOX_REDIRECT_URI,
)
from helper_func.upstox_requests import login
from pathlib import Path

def check_user_auth(env_path: Path) -> None:
    # TODO: Implement Auth and relogin of token expired
    login( client_id= UPSTOX_CLIENT_ID,
            client_secret=UPSTOX_CLIENT_SECRET,
            redirect_url= UPSTOX_REDIRECT_URI,
            forced_prod=False,
           env_path = env_path)
    pass


def relogin() -> None:
    pass
