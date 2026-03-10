"""
Notification Service for Approval System.

Handles internal messages and email notifications for approval workflow.
Supports bilingual notifications (Chinese and English).
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.models.notification import InternalMessage, EmailNotification
from src.models.approval import ApprovalRequest
from src.monitoring.report_service import EmailSender, SMTPConfig

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications to users.
    
    Handles both internal messages (站内消息) and email notifications
    with bilingual support (Chinese and English).
    """
    
    def __init__(self, db: Session, smtp_config: Optional[SMTPConfig] = None):
        """
        Initialize the Notification Service.
        
        Args:
            db: Database session
            smtp_config: Optional SMTP configuration for email sending
        """
        self.db = db
        self.email_sender = EmailSender(smtp_config)
    
    async def send_approval_request_notification(
        self,
        approver: Dict[str, Any],
        approval: ApprovalRequest,
        language: str = "zh"
    ) -> bool:
        """
        Send notification to approver about new approval request.
        
        Args:
            approver: Approver user information (must contain 'id' and 'email')
            approval: Approval request details
            language: Notification language ('zh' or 'en')
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            # Send internal message
            internal_success = await self._send_internal_message(
                approver, approval, "new_request", language
            )
            
            # Send email notification
            email_success = await self._send_email_notification(
                approver, approval, "new_request", language
            )
            
            # Log notification attempt
            logger.info(
                f"Approval notification sent to {approver.get('id')}: "
                f"internal={internal_success}, email={email_success}"
            )
            
            return internal_success or email_success
            
        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")
            return False
    
    async def send_approval_decision_notification(
        self,
        requester: Dict[str, Any],
        approval: ApprovalRequest,
        approved: bool,
        language: str = "zh"
    ) -> bool:
        """
        Send notification to requester about approval decision.
        
        Args:
            requester: Requester user information (must contain 'id' and 'email')
            approval: Approval request details
            approved: Whether the request was approved
            language: Notification language ('zh' or 'en')
            
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            decision_type = "approved" if approved else "rejected"
            
            # Send internal message
            internal_success = await self._send_internal_message(
                requester, approval, decision_type, language
            )
            
            # Send email notification
            email_success = await self._send_email_notification(
                requester, approval, decision_type, language
            )
            
            # Log notification attempt
            logger.info(
                f"Approval decision notification sent to {requester.get('id')}: "
                f"decision={decision_type}, internal={internal_success}, email={email_success}"
            )
            
            return internal_success or email_success
            
        except Exception as e:
            logger.error(f"Failed to send approval decision notification: {e}")
            return False
    
    async def _send_internal_message(
        self,
        recipient: Dict[str, Any],
        approval: ApprovalRequest,
        notification_type: str,
        language: str = "zh"
    ) -> bool:
        """
        Send internal message notification.
        
        Args:
            recipient: Recipient user information
            approval: Approval request details
            notification_type: Type of notification (new_request, approved, rejected)
            language: Message language
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Generate message content
            subject, content = self._generate_message_content(
                approval, notification_type, language
            )
            
            # Create internal message
            message = InternalMessage(
                id=str(uuid4()),
                recipient_id=recipient.get("id"),
                sender_id="system",
                subject=subject,
                content=content,
                message_type=f"approval_{notification_type}",
                related_approval_id=approval.id,
                is_read=False,
                created_at=datetime.utcnow()
            )
            
            # Store message in database
            insert_query = text("""
                INSERT INTO internal_messages (
                    id, recipient_id, sender_id, subject, content,
                    message_type, related_approval_id, is_read, created_at
                ) VALUES (
                    :id, :recipient_id, :sender_id, :subject, :content,
                    :message_type, :related_approval_id, :is_read, :created_at
                )
            """)
            
            self.db.execute(insert_query, {
                "id": message.id,
                "recipient_id": message.recipient_id,
                "sender_id": message.sender_id,
                "subject": message.subject,
                "content": message.content,
                "message_type": message.message_type,
                "related_approval_id": message.related_approval_id,
                "is_read": message.is_read,
                "created_at": message.created_at
            })
            self.db.commit()
            
            logger.info(f"Internal message sent to user {recipient.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send internal message: {e}")
            self.db.rollback()
            return False
    
    async def _send_email_notification(
        self,
        recipient: Dict[str, Any],
        approval: ApprovalRequest,
        notification_type: str,
        language: str = "zh"
    ) -> bool:
        """
        Send email notification.
        
        Args:
            recipient: Recipient user information (must contain 'email')
            approval: Approval request details
            notification_type: Type of notification (new_request, approved, rejected)
            language: Email language
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            recipient_email = recipient.get("email")
            if not recipient_email:
                logger.warning(f"No email address for user {recipient.get('id')}")
                return False
            
            # Generate email content
            subject, html_content = self._generate_email_content(
                approval, notification_type, language
            )
            
            # Send email using EmailSender
            result = await self.email_sender.send_report(
                recipient=recipient_email,
                subject=subject,
                content=html_content,
                format="html"
            )
            
            if result.success:
                logger.info(f"Email sent to {recipient_email}")
                return True
            else:
                logger.error(f"Failed to send email to {recipient_email}: {result.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _generate_message_content(
        self,
        approval: ApprovalRequest,
        notification_type: str,
        language: str
    ) -> tuple[str, str]:
        """
        Generate internal message subject and content.
        
        Args:
            approval: Approval request details
            notification_type: Type of notification
            language: Message language
            
        Returns:
            Tuple of (subject, content)
        """
        transfer_req = approval.transfer_request
        record_count = len(transfer_req.records)
        
        if language == "zh":
            if notification_type == "new_request":
                subject = "新的数据转存审批请求"
                content = f"""
您有一个新的数据转存审批请求需要处理：

审批ID: {approval.id}
申请人: {approval.requester_id}
申请人角色: {approval.requester_role}
数据源类型: {transfer_req.source_type}
目标状态: {transfer_req.target_state}
记录数量: {record_count}
申请时间: {approval.created_at.strftime('%Y-%m-%d %H:%M:%S')}
过期时间: {approval.expires_at.strftime('%Y-%m-%d %H:%M:%S')}

请及时处理此审批请求。
                """.strip()
            elif notification_type == "approved":
                subject = "您的数据转存请求已批准"
                content = f"""
您的数据转存请求已被批准：

审批ID: {approval.id}
审批人: {approval.approver_id}
批准时间: {approval.approved_at.strftime('%Y-%m-%d %H:%M:%S') if approval.approved_at else 'N/A'}
审批意见: {approval.comment or '无'}

数据转存操作已自动执行。
                """.strip()
            else:  # rejected
                subject = "您的数据转存请求已被拒绝"
                content = f"""
您的数据转存请求已被拒绝：

审批ID: {approval.id}
审批人: {approval.approver_id}
拒绝时间: {approval.approved_at.strftime('%Y-%m-%d %H:%M:%S') if approval.approved_at else 'N/A'}
拒绝原因: {approval.comment or '无'}

如有疑问，请联系审批人。
                """.strip()
        else:  # English
            if notification_type == "new_request":
                subject = "New Data Transfer Approval Request"
                content = f"""
You have a new data transfer approval request to process:

Approval ID: {approval.id}
Requester: {approval.requester_id}
Requester Role: {approval.requester_role}
Source Type: {transfer_req.source_type}
Target State: {transfer_req.target_state}
Record Count: {record_count}
Request Time: {approval.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Expiry Time: {approval.expires_at.strftime('%Y-%m-%d %H:%M:%S')}

Please process this approval request promptly.
                """.strip()
            elif notification_type == "approved":
                subject = "Your Data Transfer Request Has Been Approved"
                content = f"""
Your data transfer request has been approved:

Approval ID: {approval.id}
Approver: {approval.approver_id}
Approval Time: {approval.approved_at.strftime('%Y-%m-%d %H:%M:%S') if approval.approved_at else 'N/A'}
Comment: {approval.comment or 'None'}

The data transfer operation has been executed automatically.
                """.strip()
            else:  # rejected
                subject = "Your Data Transfer Request Has Been Rejected"
                content = f"""
Your data transfer request has been rejected:

Approval ID: {approval.id}
Approver: {approval.approver_id}
Rejection Time: {approval.approved_at.strftime('%Y-%m-%d %H:%M:%S') if approval.approved_at else 'N/A'}
Reason: {approval.comment or 'None'}

Please contact the approver if you have questions.
                """.strip()
        
        return subject, content
    
    def _generate_email_content(
        self,
        approval: ApprovalRequest,
        notification_type: str,
        language: str
    ) -> tuple[str, str]:
        """
        Generate email subject and HTML content.
        
        Args:
            approval: Approval request details
            notification_type: Type of notification
            language: Email language
            
        Returns:
            Tuple of (subject, html_content)
        """
        transfer_req = approval.transfer_request
        record_count = len(transfer_req.records)
        
        # Get plain text content first
        subject, plain_content = self._generate_message_content(
            approval, notification_type, language
        )
        
        # Convert to HTML with styling
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #1890ff;
            color: white;
            padding: 20px;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f5f5f5;
            padding: 20px;
            border-radius: 0 0 5px 5px;
        }}
        .info-row {{
            margin: 10px 0;
            padding: 10px;
            background-color: white;
            border-left: 3px solid #1890ff;
        }}
        .label {{
            font-weight: bold;
            color: #666;
        }}
        .footer {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>{subject}</h2>
    </div>
    <div class="content">
        <div class="info-row">
            <span class="label">{"审批ID" if language == "zh" else "Approval ID"}:</span> {approval.id}
        </div>
        <div class="info-row">
            <span class="label">{"数据源类型" if language == "zh" else "Source Type"}:</span> {transfer_req.source_type}
        </div>
        <div class="info-row">
            <span class="label">{"目标状态" if language == "zh" else "Target State"}:</span> {transfer_req.target_state}
        </div>
        <div class="info-row">
            <span class="label">{"记录数量" if language == "zh" else "Record Count"}:</span> {record_count}
        </div>
        <div class="info-row">
            <span class="label">{"时间" if language == "zh" else "Time"}:</span> {approval.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        </div>
        {f'<div class="info-row"><span class="label">{"审批意见" if language == "zh" else "Comment"}:</span> {approval.comment}</div>' if approval.comment else ''}
    </div>
    <div class="footer">
        <p>{"此邮件由系统自动发送，请勿回复。" if language == "zh" else "This is an automated email, please do not reply."}</p>
    </div>
</body>
</html>
        """.strip()
        
        return subject, html_content
