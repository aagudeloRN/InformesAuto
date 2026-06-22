from sqlalchemy.orm import DeclarativeBase

from ic.shared.config import get_settings


class Base(DeclarativeBase):
    metadata = __import__("sqlalchemy").MetaData(schema=get_settings().db_schema)
