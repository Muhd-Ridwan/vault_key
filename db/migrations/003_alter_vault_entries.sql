BEGIN;

    ALTER TABLE vault_entries
        DROP CONSTRAINT IF EXISTS vault_entries_entry_type_check;

    ALTER TABLE vault_entries
        ADD COLUMN IF NOT EXISTS description TEXT;

COMMIT;