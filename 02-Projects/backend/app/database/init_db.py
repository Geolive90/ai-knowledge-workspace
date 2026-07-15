from app.database.database import Base, engine

# Import all models here
from app.models import User, Document


def init_db():
    Base.metadata.create_all(bind=engine)