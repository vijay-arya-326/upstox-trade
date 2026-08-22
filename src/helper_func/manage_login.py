from helper_func.config import  (
    APPNAME,
    UPSTOX_CLIENT_ID,
    UPSTOX_CLIENT_SECRET,
    UPSTOX_REDIRECT_URI,
)
from helper_func.upstox_requests import login, sandbox_token_active
from pathlib import Path

def check_user_auth() -> None:
    active_token =  sandbox_token_active(forceProd= True)
    if active_token == False :
        #If invalid token, attempting relogin
        login()
    pass

def validate_sandbox_token():
    sandbox_token_active()


def relogin() -> None:
    pass
