import argparse
from pathlib import Path
from dotenv import load_dotenv
from bootstrap.pre_load_check import check_pre_env

# 1. Initialize the parser
parser = argparse.ArgumentParser(description="A script process UPSTOX orders. Pass env PROD|DEMO")
# 2. Add named arguments
parser.add_argument("--env", type=str, required=True, help="Demo or Prod env", choices=["prod", "demo"])
# 3. Parse the arguments
args = parser.parse_args()

env_file_name = "sandbox.env"
#LOAD ENV Based on passed arguments
if args.env.lower() == "prod":
    env_file_name="prod.env"

env_file_path = Path(__file__).parent.joinpath("env", env_file_name).resolve()
if env_file_path.exists():
    load_dotenv(dotenv_path=env_file_path, override=True)
    check_pre_env()
else:
    exit(f"Env file not found. Create a file at {env_file_path}")


from helper_func.config import APPNAME

from helper_func.download_assets import download_nse_file
from helper_func.fancy_print import fancy_print
from helper_func.manage_login import check_user_auth, validate_sandbox_token

if __name__ == "__main__":
    fancy_print(APPNAME, border_color="green")
    check_pre_env()
    download_nse_file()
    # check_user_auth(env_path = env_file_path)
    if args.env.lower() == "demo":
        validate_sandbox_token()
