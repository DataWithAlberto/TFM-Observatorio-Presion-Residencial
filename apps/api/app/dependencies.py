from app.core.database import get_engine
from app.repositories.observatory import ObservatoryRepository
from app.services.observatory import ObservatoryService
def get_service(): return ObservatoryService(ObservatoryRepository(get_engine()))
