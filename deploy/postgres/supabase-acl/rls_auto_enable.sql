-- Supabase-specific supplemental ACL hardening.
-- Not part of the portable 001/002 tenant-schema reference setup.
-- Apply only as an authorized migration owner after confirming this exact
-- function exists and no anon/authenticated application path depends on it.
-- This does not alter the function body or service_role/owner privileges.
-- Syntax reference: https://www.postgresql.org/docs/current/sql-revoke.html
REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
