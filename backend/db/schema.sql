-- SoloVibe Database Schema for Supabase/PostgreSQL

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Threads table for conversation state management
CREATE TABLE IF NOT EXISTS threads (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    thread_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    messages JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_threads_thread_id ON threads(thread_id);
CREATE INDEX IF NOT EXISTS idx_threads_status ON threads(status);
CREATE INDEX IF NOT EXISTS idx_threads_created_at ON threads(created_at);

-- Messages table for detailed message storage
CREATE TABLE IF NOT EXISTS messages (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- Checkpoints table for LangGraph state persistence
CREATE TABLE IF NOT EXISTS checkpoints (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    checkpoint_id VARCHAR(255) NOT NULL,
    state JSONB NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id ON checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_checkpoint_id ON checkpoints(checkpoint_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_timestamp ON checkpoints(timestamp);

-- Risk assessments table for action validation
CREATE TABLE IF NOT EXISTS risk_assessments (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    action_data JSONB NOT NULL,
    risk_level VARCHAR(50) NOT NULL,
    requires_confirmation BOOLEAN DEFAULT FALSE,
    assessment_result JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_assessments_thread_id ON risk_assessments(thread_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_created_at ON risk_assessments(created_at);

-- User sessions table for tracking conversation sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255), -- Can be null for anonymous users
    device_info JSONB,
    location_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);

-- Triggers for automatic updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_threads_updated_at BEFORE UPDATE ON threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_sessions_last_activity BEFORE UPDATE ON user_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) policies for Supabase
-- Enable RLS on all tables
ALTER TABLE threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Policies for anonymous access (adjust as needed for your auth strategy)
CREATE POLICY "Allow anonymous read access" ON threads
    FOR SELECT USING (true);

CREATE POLICY "Allow anonymous insert access" ON threads
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow anonymous update access" ON threads
    FOR UPDATE USING (true);

-- Similar policies for other tables
CREATE POLICY "Allow anonymous access to messages" ON messages
    FOR ALL USING (true);

CREATE POLICY "Allow anonymous access to checkpoints" ON checkpoints
    FOR ALL USING (true);

CREATE POLICY "Allow anonymous access to risk_assessments" ON risk_assessments
    FOR ALL USING (true);

CREATE POLICY "Allow anonymous access to user_sessions" ON user_sessions
    FOR ALL USING (true);

-- Sample data for testing
INSERT INTO threads (thread_id, status, messages, metadata) VALUES
    ('sample-thread-1', 'active', '[]'::jsonb, '{"source": "sample"}'::jsonb),
    ('sample-thread-2', 'waiting_confirmation', '[]'::jsonb, '{"source": "sample"}'::jsonb)
ON CONFLICT (thread_id) DO NOTHING;
