-- Create handovers table for human handover requests
CREATE TABLE IF NOT EXISTS handovers (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE SET NULL,
    itinerary_id INTEGER REFERENCES itineraries(id) ON DELETE SET NULL,
    
    -- User information
    user_message TEXT,
    user_email VARCHAR(255),
    user_phone VARCHAR(50),
    
    -- Context
    conversation_summary TEXT,
    extracted_preferences JSONB,
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
    
    -- Assignment
    assigned_to VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    contacted_at TIMESTAMP,
    resolved_at TIMESTAMP,
    
    -- Notes
    agent_notes TEXT
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_handovers_session_id ON handovers(session_id);
CREATE INDEX IF NOT EXISTS idx_handovers_status ON handovers(status);
CREATE INDEX IF NOT EXISTS idx_handovers_priority ON handovers(priority);
CREATE INDEX IF NOT EXISTS idx_handovers_created_at ON handovers(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_handovers_conversation_id ON handovers(conversation_id);
CREATE INDEX IF NOT EXISTS idx_handovers_itinerary_id ON handovers(itinerary_id);

-- Add comments
COMMENT ON TABLE handovers IS 'Tracks requests for human assistance from AI chatbot';
COMMENT ON COLUMN handovers.status IS 'pending, contacted, resolved, cancelled';
COMMENT ON COLUMN handovers.priority IS 'low, medium, high, urgent';
COMMENT ON COLUMN handovers.extracted_preferences IS 'JSON object with travel preferences extracted from conversation';
