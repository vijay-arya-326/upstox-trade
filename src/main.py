from bootstrap.pre_load_check import check_pre_env
import sys
from helper_func.config import APPNAME, LOADED_ENV, ENV_PATH
from helper_func.download_assets import download_nse_file
from helper_func.fancy_print import fancy_print
from helper_func.manage_login import check_user_auth, validate_sandbox_token

if __name__ == "__main__":
    fancy_print(APPNAME, border_color="green")
    download_nse_file()
    # check_user_auth(env_path = ENV_PATH)
    if LOADED_ENV.upper() == "DEMO":
        if not  validate_sandbox_token():
            sys.exit(1)
