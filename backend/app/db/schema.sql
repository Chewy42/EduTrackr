BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "citext";

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chat_sender_type') THEN
        CREATE TYPE chat_sender_type AS ENUM ('user', 'assistant', 'system');
    END IF;
END$$;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('UTC', NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email CITEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    password_algo TEXT NOT NULL DEFAULT 'argon2id',
    is_email_verified BOOLEAN NOT NULL DEFAULT false,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW())
);

CREATE TRIGGER trg_app_users_updated
BEFORE UPDATE ON app_users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS user_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    refresh_token_hash TEXT NOT NULL UNIQUE,
    user_agent TEXT,
    ip_address INET,
    stay_logged_in BOOLEAN NOT NULL DEFAULT false,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW())
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(user_id) WHERE revoked_at IS NULL AND expires_at > TIMEZONE('UTC', NOW());

CREATE TABLE IF NOT EXISTS user_preferences (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES app_users(id) ON DELETE CASCADE,
    stay_logged_in BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW())
);

CREATE TRIGGER trg_user_preferences_updated
BEFORE UPDATE ON user_preferences
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS program_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    storage_bucket TEXT NOT NULL DEFAULT 'program-evaluations',
    storage_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes >= 0),
    processed_at TIMESTAMPTZ,
    parsing_status TEXT NOT NULL DEFAULT 'pending',
    parsing_errors TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW())
);

CREATE INDEX IF NOT EXISTS idx_program_evaluations_user ON program_evaluations(user_id);

CREATE TABLE IF NOT EXISTS program_evaluation_sections (
    id BIGSERIAL PRIMARY KEY,
    evaluation_id UUID NOT NULL REFERENCES program_evaluations(id) ON DELETE CASCADE,
    section_name TEXT NOT NULL,
    section_order INT NOT NULL,
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW())
);

CREATE INDEX IF NOT EXISTS idx_eval_sections_evaluation_id ON program_evaluation_sections(evaluation_id);

CREATE TABLE IF NOT EXISTS student_progress_snapshots (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    evaluation_id UUID REFERENCES program_evaluations(id) ON DELETE SET NULL,
    snapshot_date DATE NOT NULL,
    metric_key TEXT NOT NULL,
    metric_value JSONB NOT NULL,
    extracted_from TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW())
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_progress_user_metric_date ON student_progress_snapshots(user_id, metric_key, snapshot_date);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    evaluation_id UUID REFERENCES program_evaluations(id) ON DELETE SET NULL,
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW()),
    archived_at TIMESTAMPTZ
);

CREATE TRIGGER trg_chat_sessions_updated
BEFORE UPDATE ON chat_sessions
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender chat_sender_type NOT NULL,
    message_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT TIMEZONE('UTC', NOW())
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at);

CREATE MATERIALIZED VIEW IF NOT EXISTS latest_student_progress AS
SELECT DISTINCT ON (user_id, metric_key)
    user_id,
    metric_key,
    metric_value,
    snapshot_date,
    created_at
FROM student_progress_snapshots
ORDER BY user_id, metric_key, snapshot_date DESC, created_at DESC;

ALTER TABLE app_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE program_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE program_evaluation_sections ENABLE ROW LEVEL SECURITY;
ALTER TABLE student_progress_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY IF NOT EXISTS "Users can read/update themselves"
    ON app_users
    FOR ALL
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users manage their preferences"
    ON user_preferences
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users manage their sessions"
    ON user_sessions
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users manage their evaluations"
    ON program_evaluations
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users manage their evaluation sections"
    ON program_evaluation_sections
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM program_evaluations pe
            WHERE pe.id = program_evaluation_sections.evaluation_id
              AND pe.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM program_evaluations pe
            WHERE pe.id = program_evaluation_sections.evaluation_id
              AND pe.user_id = auth.uid()
        )
    );

CREATE POLICY IF NOT EXISTS "Users manage their progress"
    ON student_progress_snapshots
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users manage their chat sessions"
    ON chat_sessions
    FOR ALL
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY IF NOT EXISTS "Users manage their chat messages"
    ON chat_messages
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM chat_sessions cs
            WHERE cs.id = chat_messages.session_id
              AND cs.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM chat_sessions cs
            WHERE cs.id = chat_messages.session_id
              AND cs.user_id = auth.uid()
        )
    );

COMMIT;
