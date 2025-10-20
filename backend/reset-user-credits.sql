-- Reset user credits to Pro plan amount (40)
-- Run this in psql or your database client

-- Check current credits
SELECT id, email, credits, total_credits_used FROM "user" WHERE id = 'user_32YpX6nzyOe3gPadIBk2lwozNQH';

-- Reset to 40 (Pro plan monthly allowance)
UPDATE "user"
SET credits = 40,
    total_credits_used = 0
WHERE id = 'user_32YpX6nzyOe3gPadIBk2lwozNQH';

-- Verify update
SELECT id, email, credits, total_credits_used FROM "user" WHERE id = 'user_32YpX6nzyOe3gPadIBk2lwozNQH';
