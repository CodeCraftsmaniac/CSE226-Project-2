CREATE TABLE IF NOT EXISTS cse226_ocr_device_codes (
    device_code VARCHAR(32) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    token TEXT,
    user_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cse226_ocr_device_codes_status_expires
    ON cse226_ocr_device_codes(status, expires_at DESC);

ALTER TABLE cse226_ocr_device_codes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "cse226_ocr_device_codes_policy" ON cse226_ocr_device_codes;

CREATE POLICY "cse226_ocr_device_codes_policy"
    ON cse226_ocr_device_codes
    FOR ALL
    USING (true)
    WITH CHECK (true);
