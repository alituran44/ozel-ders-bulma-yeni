-- SQLite Database Schema for Private Tutoring Leads

CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,               -- UUID string
    platform TEXT NOT NULL,            -- 'Twitter', 'Sahibinden', 'DonanımHaber', etc.
    original_date TEXT,                -- The date/time raw string from the post
    content TEXT NOT NULL,             -- The full content of the request
    subject TEXT,                      -- Extracted branch (Matematik, Fizik, vb.)
    location TEXT,                     -- Predicted city/district
    contact_info TEXT,                 -- Extracted phone or email
    whatsapp_link TEXT,                -- Pre-built WhatsApp click-to-chat URL
    original_link TEXT UNIQUE,         -- URL to the post
    text_hash TEXT UNIQUE,             -- Hash of the content for deduplication
    is_qualified INTEGER DEFAULT 1,    -- 1 for qualified (LEAD), 0 for not (AD)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_leads_platform ON leads(platform);
CREATE INDEX IF NOT EXISTS idx_leads_subject ON leads(subject);
CREATE INDEX IF NOT EXISTS idx_leads_location ON leads(location);
