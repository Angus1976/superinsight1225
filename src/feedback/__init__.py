"""
Feedback management module for SuperInsight Platform.

Provides:
- Feedback collection and sentiment analysis
- Feedback processing and SLA management
- Feedback-driven improvement engine
- Customer relationship management
"""

def get_feedback_collector():
    """Get FeedbackCollector instance with lazy import."""
    from .collector import FeedbackCollector
    return FeedbackCollector()


def get_feedback_processor():
    """Get FeedbackProcessor instance with lazy import."""
    from .processor import FeedbackProcessor
    return FeedbackProcessor()


def get_improvement_engine():
    """Get ImprovementEngine instance with lazy import."""
    from .improvement_engine import ImprovementEngine
    return ImprovementEngine()


__all__ = [
    "get_feedback_collector",
    "get_feedback_processor",
    "get_improvement_engine",
]
