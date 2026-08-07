-- Add missing columns to User table for credit reset tracking
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "planAnniversaryAt" TIMESTAMP;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "lastCreditResetAt" TIMESTAMP;

-- Add GST fields if they don't exist
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "userGstin" VARCHAR;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "userGstName" VARCHAR;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "userGstAddress" VARCHAR;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "userGstState" VARCHAR;
ALTER TABLE "User" ADD COLUMN IF NOT EXISTS "userGstStateCode" VARCHAR;
