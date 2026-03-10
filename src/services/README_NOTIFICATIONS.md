# Approval Notification System

## Overview

The approval notification system provides bilingual (Chinese/English) notifications for the data transfer approval workflow. It supports both internal messages (站内消息) and email notifications.

## Components

### 1. NotificationService (`notification_service.py`)

Main service for sending notifications with the following features:

- **Bilingual Support**: Automatically generates Chinese and English content
- **Dual Channel**: Sends both internal messages and emails
- **HTML Email**: Styled HTML emails with responsive design
- **Error Handling**: Graceful degradation if one channel fails

#### Key Methods

```python
# Send notification when approval request is created
await notification_service.send_approval_request_notification(
    approver=approver_dict,
    approval=approval_request,
    language="zh"  # or "en"
)

# Send notification when approval decision is made
await notification_service.send_approval_decision_notification(
    requester=requester_dict,
    approval=approval_request,
    approved=True,  # or False for rejection
    language="zh"
)
```

### 2. ApprovalService Integration

The `ApprovalService` automatically triggers notifications at key points:

- **On Approval Creation**: Notifies all eligible approvers (data_manager and admin roles)
- **On Approval Decision**: Notifies the requester of approval/rejection

#### Implementation Details

```python
# In ApprovalService.__init__
self.notification_service = NotificationService(db)

# Notifications are sent automatically
approval = await approval_service.create_approval_request(...)
# -> Triggers _notify_approvers() -> sends notifications

await approval_service.approve_request(...)
# -> Triggers _notify_requester() -> sends decision notification
```

### 3. Database Schema

#### Internal Messages Table

```sql
CREATE TABLE internal_messages (
    id VARCHAR(36) PRIMARY KEY,
    recipient_id VARCHAR(36) NOT NULL,
    sender_id VARCHAR(36),
    subject VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    related_approval_id VARCHAR(36),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    
    FOREIGN KEY (recipient_id) REFERENCES users(id),
    FOREIGN KEY (related_approval_id) REFERENCES approval_requests(id)
);
```

## Usage Examples

### Example 1: Creating an Approval (Automatic Notifications)

```python
from src.services.approval_service import ApprovalService

approval_service = ApprovalService(db_session)

# Create approval - notifications sent automatically
approval = await approval_service.create_approval_request(
    transfer_request=transfer_request,
    requester_id="user-123",
    requester_role=UserRole.DATA_ANALYST
)

# All eligible approvers receive:
# 1. Internal message notification
# 2. Email notification
```

### Example 2: Approving a Request (Automatic Notifications)

```python
# Approve request - requester notified automatically
await approval_service.approve_request(
    approval_id="approval-456",
    approver_id="approver-789",
    approver_role=UserRole.DATA_MANAGER,
    approved=True,
    comment="Data quality looks good"
)

# Requester receives:
# 1. Internal message with approval details
# 2. Email with approval details and comment
```

### Example 3: Manual Notification Sending

```python
from src.services.notification_service import NotificationService

notification_service = NotificationService(db_session)

# Send custom notification
await notification_service.send_approval_request_notification(
    approver={
        "id": "user-123",
        "email": "user@example.com",
        "username": "john_doe"
    },
    approval=approval_request,
    language="en"  # English notification
)
```

## Notification Content

### Chinese Notification Example

**Subject**: 新的数据转存审批请求

**Content**:
```
您有一个新的数据转存审批请求需要处理：

审批ID: approval-123
申请人: user-456
申请人角色: data_analyst
数据源类型: structuring
目标状态: in_sample_library
记录数量: 15
申请时间: 2026-03-10 10:00:00
过期时间: 2026-03-17 10:00:00

请及时处理此审批请求。
```

### English Notification Example

**Subject**: New Data Transfer Approval Request

**Content**:
```
You have a new data transfer approval request to process:

Approval ID: approval-123
Requester: user-456
Requester Role: data_analyst
Source Type: structuring
Target State: in_sample_library
Record Count: 15
Request Time: 2026-03-10 10:00:00
Expiry Time: 2026-03-17 10:00:00

Please process this approval request promptly.
```

## Email Configuration

The notification system uses the existing `EmailSender` from `src/monitoring/report_service.py`.

### SMTP Configuration

Set the following environment variables:

```bash
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=noreply@example.com
SMTP_PASSWORD=your_password
SMTP_USE_TLS=true
SMTP_FROM_ADDRESS=noreply@example.com
SMTP_FROM_NAME=SuperInsight Platform
```

### Email Features

- **HTML Format**: Styled emails with responsive design
- **Retry Mechanism**: Automatic retry with exponential backoff
- **Fallback**: Plain text version included for email clients that don't support HTML
- **Error Handling**: Failures logged but don't block approval workflow

## Testing

### Unit Tests

```bash
python3 -m pytest tests/unit/test_notification_service.py -v
```

Tests cover:
- Internal message creation
- Email sending
- Bilingual content generation
- Error handling
- HTML formatting

### Integration Tests

```bash
python3 -m pytest tests/integration/test_approval_notifications.py -v
```

Tests cover:
- Complete notification flow
- Database integration
- Approval workflow integration
- Error resilience

## Error Handling

The notification system is designed to be resilient:

1. **Partial Failure**: If email fails but internal message succeeds, the notification is considered successful
2. **Non-Blocking**: Notification failures don't prevent approval creation or processing
3. **Logging**: All failures are logged for monitoring
4. **Graceful Degradation**: Missing email addresses or SMTP configuration don't cause crashes

## Future Enhancements

Potential improvements for future versions:

1. **User Preferences**: Allow users to configure notification language and channels
2. **Notification Templates**: Support customizable notification templates
3. **Additional Channels**: Add SMS, WeChat, Slack notifications
4. **Notification History**: UI for viewing notification history
5. **Read Receipts**: Track when users read internal messages
6. **Batch Notifications**: Optimize for high-volume scenarios

## Related Files

- `src/services/notification_service.py` - Main notification service
- `src/services/approval_service.py` - Approval workflow with notification integration
- `src/models/notification.py` - Notification data models
- `src/database/migrations/create_internal_messages_table.sql` - Database schema
- `tests/unit/test_notification_service.py` - Unit tests
- `tests/integration/test_approval_notifications.py` - Integration tests
