from sqlalchemy import create_engine
from .config import get_settings
_engine=None
def get_engine():
    global _engine
    if _engine is None: _engine=create_engine(get_settings().database_url,pool_pre_ping=True)
    return _engine
