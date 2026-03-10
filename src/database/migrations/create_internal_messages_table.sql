-- Migration: Create internal_messages table for approval notifications
-- Created: 2026-03-10
-- Description: Stores internal notification messages for approval workflow

CREATE TABLE IF NOT EXISTS internal_messages (
    id VARCHAR(36) PRIMARY KEY,
    recipient_id VARCHAR(36) NOT NULL,
    sender_id VARCHAR(36),
    subject VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(50) NOT NULL DEFAULT 'approval_notification',
    related_approval_id VARCHAR(36),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    
    -- Indexes for performance
    INDEX idx_recipient_id (recipient_id),
    INDEX idx_message_type (message_type),
    INDEX idx_related_approval_id (related_approval_id),
    INDEX idx_is_read (is_read),
    INDEX idx_created_at (created_at),
    
    -- Foreign key constraints (if users table exists)
    FOREIGN KEY (recipient_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (related_approval_id) REFERENCES approval_requests(id) ON DELETE CASCADE
);

-- Add comment to table
COMMENT ON TABLE internal_messages IS 'Internal notification messages for approval workflow';

-- Add comments to columns
COMMENT ON COLUMN internal_messages.id IS 'Unique message identifier';
COMMENT ON COLUMN internal_messages.recipient_id IS 'User ID of message recipient';
COMMENT ON COLUMN internal_messages.sender_id IS 'User ID of message sender (NULL for system messages)';
COMMENT ON COLUMN internal_messages.subject IS 'Message subject line';
COMMENT ON COLUMN internal_messages.content IS 'Message content body';
COMMENT ON COLUMN internal_messages.message_type IS 'Type of message (approval_new_request, approval_approved, approval_rejected)';
COMMENT ON COLUMN internal_messages.related_approval_id IS 'Related approval request ID';
COMMENT ON COLUMN internal_messages.is_read IS 'Whether message has been read';
COMMENT ON COLUMN internal_messages.created_at IS 'Message creation timestamp';
COMMENT ON COLUMN internal_messages.read_at IS 'Message read timestamp';
