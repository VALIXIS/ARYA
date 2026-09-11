-- PROJECT ARYA - SUPABASE / CLOUD POSTGRESQL MIGRATION SCHEMA

CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'Other',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversation (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goals (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);

-- SEED SUBHASH PERSONAL DATA
INSERT INTO memories (content, category) VALUES ('My name is Subhash. Please address me as Subhash or Sir.', 'Identity');
INSERT INTO memories (content, category) VALUES ('I study Artificial Intelligence and Machine Learning (AIML) at VVITU.', 'Education');
INSERT INTO memories (content, category) VALUES ('My ultimate goal is to become an elite AI Engineer and launch my own AI technology company.', 'Goals');
INSERT INTO memories (content, category) VALUES ('I built Project ARYA, a 24/7 production-grade autonomous personal AI assistant operating across cloud, desktop, and mobile.', 'Projects');
INSERT INTO memories (content, category) VALUES ('I built Planly, an autonomous AI-powered scheduling and productivity platform.', 'Projects');
INSERT INTO memories (content, category) VALUES ('I am passionate about photography, high-end video editing, autonomous AI agents, and cutting-edge tech innovation.', 'Interests');
INSERT INTO memories (content, category) VALUES ('My favourite film actor is Prabhas.', 'Preferences');
INSERT INTO memories (content, category) VALUES ('I love listening to Telugu music and energetic soundtrack instrumental tracks.', 'Preferences');
INSERT INTO memories (content, category) VALUES ('My primary laptop is SUBHASH-ASUS (ASUS Laptop running Windows 11 with 16GB RAM).', 'Devices');
INSERT INTO memories (content, category) VALUES ('My primary mobile device is I2302 (Android smartphone with PIN 9603).', 'Devices');
INSERT INTO memories (content, category) VALUES ('I prefer brief, sharp, highly intelligent responses from ARYA with automatic voice readback enabled.', 'Workflow');
INSERT INTO memories (content, category) VALUES ('PROJECT ARYA operates as a cloud-native, multi-provider AI assistant using Groq (llama-3.3-70b), Gemini 2.0 Flash, and local Ollama (qwen2.5:3b).', 'System');
INSERT INTO memories (content, category) VALUES ('Completed key goal: AI Engineering Internship.', 'Goals');
INSERT INTO memories (content, category) VALUES ('Project ARYA has a built-in memory graph, compound intent planner, multi-device relay, and Web Speech voice interface.', 'Knowledge');
INSERT INTO goals (title, status) VALUES ('to get an AI internship', 'completed');
