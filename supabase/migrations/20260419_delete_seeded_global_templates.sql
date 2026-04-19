-- Remove seeded generic templates that were inserted with user_id = NULL.
-- These are test data, not crew-owned schedules. MLC 2006 Reg 2.3 requires
-- crew to manage their own schedule records — shared "generic" templates
-- conflict with the personal ownership model.
--
-- Run on TENANT DB: vzsohavtuotocgrfkfyd
-- Safe to run multiple times (idempotent).

DELETE FROM pms_crew_normal_hours
WHERE user_id IS NULL;
