from app.models.booking import Base
from app.db.session import engine

Base.metadata.create_all(bind=engine)
