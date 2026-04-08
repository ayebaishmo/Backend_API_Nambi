-- Add language support to conversations table
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'en' NOT NULL;

-- Create index for language queries
CREATE INDEX IF NOT EXISTS idx_conversations_language ON conversations(language);

-- Add comment
COMMENT ON COLUMN conversations.language IS 'User preferred language code (en, fr, de, es, sw, etc.)';
