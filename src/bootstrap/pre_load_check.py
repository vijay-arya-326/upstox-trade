import os
from datetime import  datetime
from helper_func.fancy_print import fancy_print


def check_env_variables():
    error_flag = False
    error_messages = []
    warning_messages = []

    mandatory_variables = [
        "APPNAME",
        "LOADED_ENV",
        "INSTRUMENT_FILE",
        "INSTRUMENT_FILE_PICKLE",
        "SANDBOX_UPSTOX_URL",
        "UPSTOX_URL",
        "UPSTOX_HF_API_URL",
        "UPSTOX_ACCESS_TOKEN",
        "UPSTOX_EXTENDED_TOKEN",
        "UPSTOX_CLIENT_ID",
        "UPSTOX_CLIENT_SECRET",
        "SANDBOX_ACCESS_TOKEN",
    ]

    optional_variables = [

    ]

    for var in mandatory_variables:
        if not (os.getenv(var) or "").strip():
            error_flag = True
            error_messages.append(f"Mandatory environment variable \"{var}\" is not set.")

    for var in optional_variables:
        if not (os.getenv(var) or "").strip():
            warning_messages.append(f"Optional Environment Variable \"{var}\" Missing")

    # checking for past expiry dates
    expiry_date = (os.getenv("EXPIRY_DATE") or "").strip()
    if expiry_date and expiry_date < datetime.now().strftime("%Y-%m-%d"):
        error_flag = True
        error_messages.append(f"Expiry date \"{expiry_date}\" is in the past.")

    return {"error_flag": error_flag, "error_messages": error_messages, "warning_messages": warning_messages}


def check_pre_env():
    env_checking_response = check_env_variables()

    if env_checking_response["warning_messages"]:
        for message in env_checking_response["warning_messages"]:
            fancy_print(message, border_color="yellow")

    if env_checking_response["error_messages"]:
        for message in env_checking_response["error_messages"]:
            fancy_print(message, border_color="red")

    if env_checking_response["error_flag"]:
        fancy_print("Add and Update Mandatory Environment Variables in .env file and restart the application", border_color="red")
        exit(1)
