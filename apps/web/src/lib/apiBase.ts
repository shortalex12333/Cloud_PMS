/**
 * API Base URL — single source of truth.
 *
 * TEMPORARY: Docker staging fallback is localhost:8000.
 * When moving to production: ensure NEXT_PUBLIC_API_URL is set in Vercel env vars.
 * To change the staging port: update DOCKER_STAGING_URL here only — nowhere else.
 */

// TEMP — Docker staging. Change port here when decided.
export const DOCKER_STAGING_URL = 'http://localhost:8000';

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || DOCKER_STAGING_URL;
