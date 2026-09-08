"""计算传播论文追踪系统 - 核心模块"""

from .storage import PaperStorage
from .notification import NotificationSender
from .config import Config

def __getattr__(name: str):
    if name == "PaperDiscovery":
        from .discovery import PaperDiscovery
        return PaperDiscovery
    if name == "PaperFilter":
        from .filter import PaperFilter
        return PaperFilter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "PaperDiscovery",
    "PaperFilter",
    "PaperStorage",
    "NotificationSender",
    "Config",
]
