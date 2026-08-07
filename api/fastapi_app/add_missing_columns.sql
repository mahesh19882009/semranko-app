-- Add missing columns to User table for credit reset tracking
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "planAnniversaryAt" TIMESTAMP;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "lastCreditResetAt" TIMESTAMP;

-- Add DataForSEOCost table if it doesn't exist
CREATE TABLE IF NOT EXISTS "DataForSEOCost" (
    "id" VARCHAR PRIMARY KEY,
    "userId" VARCHAR,
    "taskType" VARCHAR NOT NULL,
    "endpoint" VARCHAR NOT NULL,
    "costCredits" FLOAT NOT NULL,
    "costUsd" FLOAT,
    "keywordCount" INTEGER DEFAULT 1,
    "meta" JSONB,
    "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY ("userId") REFERENCES "User"(id) ON DELETE SET NULL
);

-- Create indexes for DataForSEOCost
CREATE INDEX IF NOT EXISTS "DataForSEOCost_userId_idx" ON "DataForSEOCost"("userId");
CREATE INDEX IF NOT EXISTS "DataForSEOCost_createdAt_idx" ON "DataForSEOCost"("createdAt");
CREATE INDEX IF NOT EXISTS "DataForSEOCost_taskType_idx" ON "DataForSEOCost"("taskType");
