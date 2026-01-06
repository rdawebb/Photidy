"""View definitions for the application"""

from .progress import ProgressView
from .results import ResultsView
from .setup import SetupView
from .summary import SummaryView

__all__ = [
    "ProgressView",
    "ResultsView",
    "SetupView",
    "SummaryView",
]
