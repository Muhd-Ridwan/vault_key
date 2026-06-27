BEGIN;

CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY DEFAULT 1,
    vault_visibility TEXT NOT NULL DEFAULT 'shared' CHECK (vault_visibility IN ('shared', 'private')),
    CONSTRAINT single_row CHECK (id = 1)
);

INSERT INTO app_settings (id, vault_visibility) VALUES (1, 'shared') ON CONFLICT (id) DO NOTHING;

COMMIT;