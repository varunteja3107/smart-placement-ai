from database import Base, engine
from models import ApplicationRecord

Base.metadata.create_all(bind=engine)

print("Tables created or already exist:")
print(Base.metadata.tables.keys())
