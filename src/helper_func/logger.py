import json
import requests
from helper_func.config import DB_PATH_FULL
from db.helper.db_connector import db_session, get_engine, orm_session
from db.models.api_log import ApiLog
from datetime import datetime

def api_logger(url:str, method:str, headers:dict, api_response:requests.Response, payload:dict):
    log =  ApiLog(
        url=url,
        method=method,
        headers=json.dumps(headers),
        status_code=api_response.status_code,
        api_response=json.dumps(api_response.json()),
        payload=json.dumps(payload),
        created_at=datetime.now().replace(microsecond=0)
    )

    with orm_session() as session:
        session.add(log)
        session.commit()
        session.refresh(log)
