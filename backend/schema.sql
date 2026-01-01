-- Personal AI OS - Database Schema
-- PostgreSQL schema for the Personal AI OS system

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table (simplified, supports multi-tenancy)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Rules table - core entity for learned preferences
CREATE TABLE rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Rule content
    content TEXT NOT NULL,                    -- The generalized rule
    original_correction TEXT,                  -- User's original correction
    category VARCHAR(50) NOT NULL,            -- style|tone|formatting|logic|safety
    
    -- Confidence tracking
    confidence FLOAT DEFAULT 0.5,             -- 0-1 score
    times_applied INTEGER DEFAULT 0,
    times_reinforced INTEGER DEFAULT 0,
    
    -- Status
    status VARCHAR(20) DEFAULT 'active',      -- active|archived|disabled
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_applied_at TIMESTAMP,
    last_reinforced_at TIMESTAMP,
    
    -- Vector store reference
    embedding_id VARCHAR(255)
);

-- Interactions table - for memory and context
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    conversation_id VARCHAR(255),
    
    -- Message content
    user_message TEXT NOT NULL,
    assistant_response TEXT NOT NULL,
    
    -- Rules that were applied
    rules_applied UUID[],
    
    -- Correction tracking
    was_corrected BOOLEAN DEFAULT FALSE,
    correction_text TEXT,
    extracted_rule_id UUID REFERENCES rules(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Vector store reference
    embedding_id VARCHAR(255)
);

-- Audit log for transparency
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES rules(id) ON DELETE SET NULL,
    
    event_type VARCHAR(50) NOT NULL,          -- created|applied|reinforced|decayed|archived|edited|deleted
    event_data JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_rules_user_status ON rules(user_id, status);
CREATE INDEX idx_rules_confidence ON rules(confidence DESC);
CREATE INDEX idx_rules_category ON rules(category);
CREATE INDEX idx_interactions_user ON interactions(user_id);
CREATE INDEX idx_interactions_conversation ON interactions(conversation_id);
CREATE INDEX idx_interactions_corrected ON interactions(was_corrected) WHERE was_corrected = TRUE;
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_rule ON audit_logs(rule_id);
CREATE INDEX idx_audit_logs_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rules_updated_at
    BEFORE UPDATE ON rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
