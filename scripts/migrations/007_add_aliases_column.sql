-- Migration 007: Add aliases JSONB column to entidades table (Spec 007 / DT-050b)
-- Ensures idempotency across all database setups.

ALTER TABLE ic.entidades ADD COLUMN IF NOT EXISTS aliases JSONB DEFAULT '[]'::jsonb;
ALTER TABLE entidades ADD COLUMN IF NOT EXISTS aliases JSONB DEFAULT '[]'::jsonb;
