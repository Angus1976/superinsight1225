"""
Collaboration Workflow Module (协作与审核流程)

This module provides comprehensive collaboration and review workflow functionality:
- Task Dispatcher: Intelligent task assignment based on skills and workload
- Collaboration Engine: Multi-user collaboration with real-time sync
- Review Flow Manager: Multi-level review process management
- Conflict Resolver: Annotation conflict detection and resolution
- Quality Controller: Quality monitoring and control
- Notification Service: Multi-channel notifications
- Crowdsource Manager: Crowdsourcing task management
- Crowdsource Billing: Crowdsourcing billing and settlement
- Third Party Platform Adapter: Integration with external platforms
"""

from .task_dispatcher import TaskDispatcher, AssignmentMode
from .collaboration_engine import CollaborationEngine
from .review_flow_manager import ReviewFlowManager, ReviewStatus
from .conflict_resolver import ConflictResolver
from .quality_controller import QualityController
from .notification_service import NotificationService
from .crowdsource_manager import CrowdsourceManager
from .crowdsource_annotator_manager import CrowdsourceAnnotatorManager, AnnotatorStatus
from .crowdsource_billing import CrowdsourceBilling
from .third_party_platform_adapter import ThirdPartyPlatformAdapter

__all__ = [
    "TaskDispatcher",
    "AssignmentMode",
    "CollaborationEngine",
    "ReviewFlowManager",
    "ReviewStatus",
    "ConflictResolver",
    "QualityController",
    "NotificationService",
    "CrowdsourceManager",
    "CrowdsourceAnnotatorManager",
    "AnnotatorStatus",
    "CrowdsourceBilling",
    "ThirdPartyPlatformAdapter",
]
