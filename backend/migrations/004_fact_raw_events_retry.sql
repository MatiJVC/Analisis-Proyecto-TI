-- =============================================================================
-- Migration 004 — ETL retry tracking columns for fact_raw_events
-- Adds retry_count and failed to support bounded ETL retry with dead-letter
-- semantics. Events that exceed MAX_ETL_RETRIES are marked failed=TRUE and
-- permanently removed from the retry queue.
-- =============================================================================

ALTER TABLE fact_raw_events
    ADD COLUMN IF NOT EXISTS retry_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE fact_raw_events
    ADD COLUMN IF NOT EXISTS failed BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN fact_raw_events.retry_count IS 'Number of failed ETL attempts; incremented by _run_etl on each exception';
COMMENT ON COLUMN fact_raw_events.failed      IS 'TRUE when retry_count reaches MAX_ETL_RETRIES; event is never retried again';

-- Replace the old ETL partial index (processed, source) with one that also
-- excludes permanently-failed events, keeping the index small and the retry
-- query fast.
DROP INDEX IF EXISTS idx_fre_processed_source;

CREATE INDEX IF NOT EXISTS idx_fre_pending
    ON fact_raw_events (processed, failed, ingested_at)
    WHERE processed = FALSE AND failed = FALSE;

-- =============================================================================
-- Rollback
-- =============================================================================
-- ALTER TABLE fact_raw_events DROP COLUMN IF EXISTS retry_count;
-- ALTER TABLE fact_raw_events DROP COLUMN IF EXISTS failed;
-- DROP INDEX IF EXISTS idx_fre_pending;
-- Restore old index:
-- CREATE INDEX IF NOT EXISTS idx_fre_processed_source
--     ON fact_raw_events (processed, source) WHERE processed = FALSE;