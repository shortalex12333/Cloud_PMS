/**
 * Keep-warm cron — fires every 10 minutes via Vercel Crons.
 *
 * Pings both Render services to prevent free-tier hibernation.
 * Render hibernates services after ~15 minutes of inactivity.
 * A hibernated service returns HTML with no CORS headers, which
 * causes CORS errors in the browser on bootstrap and a 503 from
 * the Next.js HoR proxy.
 *
 * Schedule: every 10 minutes (see vercel.json crons config).
 * No auth required — this endpoint makes no mutations and returns
 * only service health status. Worst case abuse: someone pings our
 * own /health endpoints.
 */

import { NextResponse } from 'next/server';

const SERVICES = [
  process.env.NEXT_PUBLIC_API_URL || 'https://pipeline-core.int.celeste7.ai',
  'https://backend.celeste7.ai',
  'https://pipeline-core.int.celeste7.ai',
];

// Deduplicate in case NEXT_PUBLIC_API_URL is already pipeline-core
const UNIQUE_SERVICES = [...new Set(SERVICES)];

export const runtime = 'nodejs';
// 55s: Render free-tier cold boot takes 30-60s. Must be < Vercel's 60s limit.
export const maxDuration = 55;

export async function GET() {
  const results: Record<string, number | string> = {};

  await Promise.allSettled(
    UNIQUE_SERVICES.map(async (url) => {
      const target = `${url}/health`;
      try {
        // 50s timeout — enough for a full Render cold-start boot cycle
        const res = await fetch(target, {
          signal: AbortSignal.timeout(50_000),
          cache: 'no-store',
        });
        results[url] = res.status;
      } catch (err: unknown) {
        results[url] = err instanceof Error ? err.message : 'error';
      }
    }),
  );

  const allWarm = Object.values(results).every((v) => v === 200);

  return NextResponse.json(
    { ok: allWarm, services: results, ts: new Date().toISOString() },
    { status: allWarm ? 200 : 207 },
  );
}
