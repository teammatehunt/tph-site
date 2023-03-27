from abc import ABC, abstractmethod
from typing import Any

from spoilr.core.models import User


class BasePuzzleHandler(ABC):
    """Abstract class for handling websocket data."""

    @staticmethod
    @abstractmethod
    def process_data(user: User, uuid: str, data: Any, **kwargs):
        """Callback when JSON data is received from the client."""
        pass

    @staticmethod
    def connect(user: User, uuid: str, slug: str = None):
        """Callback when a user connects."""
        pass

    @staticmethod
    def disconnect(user: User, uuid: str, slug: str = None):
        """Callback when a user disconnects."""
        pass
