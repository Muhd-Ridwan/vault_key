BEGIN;

CREATE TABLE IF NOT EXISTS totp_devices (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label         TEXT NOT NULL,
    secret        BYTEA NOT NULL,
    confirmed     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_totp_devices_user_id ON totp_devices (user_id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'totp_secrets') THEN
        INSERT INTO totp_devices (user_id, label, secret, confirmed, created_at)
        SELECT user_id, 'Device 1', secret, confirmed, created_at
        FROM totp_secrets;

        DROP TABLE totp_secrets;
    END IF;
END $$;

ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_action_check;
ALTER TABLE audit_log ADD CONSTRAINT audit_log_action_check CHECK (action IN (
    'view', 'create', 'update', 'delete', 'login',
    'approve_user', 'reject_user', 'revoke_user',
    'reset_totp', 'enroll_totp', 'update_settings',
    'add_totp_device', 'delete_totp_device'
));

COMMIT;