from sqlalchemy import text
from database import engine

with engine.connect() as connection:
    result = connection.execute(
        text("SELECT DATABASE(), VERSION()")
    )
    print("MySQL connection successful:", result.fetchone())
