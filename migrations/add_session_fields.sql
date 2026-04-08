-- Migration: Add session management fields to conversations table
-- Run this SQL script on your database

ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_expires_at ON conversations(expires_at);
CREATE INDEX IF NOT EXISTS idx_conversations_is_active ON conversations(is_active);
CREATE INDEX IF NOT EXISTS idx_conversations_last_activity ON conversations(last_activity);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_session_id ON bookings(session_id);
CREATE INDEX IF NOT EXISTS idx_bookings_created_at ON bookings(created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_message_id ON feedback(message_id);

-- Update existing conversations to have expiration
UPDATE conversations 
SET expires_at = created_at + INTERVAL '30 minutes',
    last_activity = updated_at
WHERE expires_at IS NULL;
