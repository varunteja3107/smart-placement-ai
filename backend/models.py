from sqlalchemy import Column, String, Float
from database import Base


class ApplicationRecord(Base):
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(30), nullable=False, index=True)
    job_title = Column(String(200), nullable=False)
    company = Column(String(200), nullable=False)
    student_name = Column(String(100), nullable=False)
    student_email = Column(String(254), nullable=False, index=True)
    cgpa = Column(Float, nullable=False)
    status = Column(String(30), nullable=False, default="Applied")
    created_at = Column(String(40), nullable=False)
