BEGIN;

ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS audit_log_action_check;

ALTER TABLE audit_log ADD CONSTRAINT audit_log_action_check CHECK (action IN ('view', 'create', 'update', 'delete', 'login', 'approve_user', 'reject_user', 'revoke_user','reset_totp'));

COMMIT;