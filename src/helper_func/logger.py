import json
import requests
from requests import Response

from helper_func.config import DB_PATH_FULL
from db.helper.db_connector import db_session, get_engine, orm_session
from db.models.api_log import ApiLog
from datetime import datetime

def api_logger(url:str, method:str, headers:dict, api_response: Response, payload:dict):
    # print("From API Logger ::", api_response.status_code)
    try:
        body = json.dumps(api_response.json())
    except Exception:
        body = api_response.text or None

    log =  ApiLog(
        url=url,
        method=method,
        headers=json.dumps(headers) if headers is not None else None,
        response_status=api_response.status_code,
        response= body,
        payload= json.dumps(payload) if payload is not None else None,
        created_at=datetime.now().replace(microsecond=0)
    )

    with orm_session() as session:
        session.add(log)
        session.commit()
        session.refresh(log)
