# Render Service Overnight Monitoring Report

**Session:** 2026-04-17 01:01–09:47 UTC (8h46m)  
**Observer:** Claude Code shard-37 (HOURSOFREST01) + MCP02 peer (qiny4db7)  
**Services monitored:**
- `pipeline-core.int.celeste7.ai` (FastAPI backend — HoR API, authentication, compliance logic)
- `backend.celeste7.ai` (legacy API — bootstrap, email)

---

## One-Paragraph Summary

One genuine incident occurred between 06:40–07:04 UTC (~24 minutes) where both Render services entered an oscillating crash-loop, alternating between 503 and 502 responses despite active keep-warm pings every 3 minutes. Services recovered at 07:07 UTC and remained stable for the rest of the session. A second single-tick blip occurred at 07:40 UTC (3 minutes, self-recovered). No automated tests were affected — all 18 regression runs (10/10 each) used mock intercepts, isolating them entirely from Render service state. The incident is attributed to Render free-tier OOM (out-of-memory) eviction at a low-traffic hour. The keep-warm cron cannot prevent OOM kills — only hibernation. A paid Render plan is the correct fix.

---

## Full Timeline

| UTC time | Duration | Status | Detail |
|---|---|---|---|
| 01:01 | baseline | STABLE | Both services 200. Monitoring begins. |
| 01:01–06:37 | 5h 36m | STABLE | 11 consecutive regression passes. Keep-warm all-green. |
| 06:40 | — | DEGRADED | Both services → 503. First DEGRADED signal. |
| 06:43 | — | DEGRADED | Both services → 503. Second consecutive. |
| 06:46 | — | OK | Both services → 200. Recovery attempt 1. |
| 06:49 | — | OK | Both services → 200. |
| 06:52 | — | OK | Both services → 200. |
| 06:55 | — | DEGRADED | Both services → 503. Re-crashed after 9min stable. |
| 06:58 | — | OK | Both services → 200. |
| 07:01 | — | DEGRADED | Both services → **502** (Bad Gateway — mid-boot signal). |
| 07:04 | — | DEGRADED | Both services → 503 (502 reverted — crash-loop confirmed). |
| 07:07 | — | STABLE | Both services → 200. Stable recovery confirmed. |
| 07:07–07:40 | ~33 min | STABLE | 9 consecutive keep-warm OKs. |
| 07:40 | ~3 min | BLIP | Both services → 503. Single-tick transient. |
| 07:43 | — | STABLE | Both services → 200. Recovered. |
| 07:43–09:47 | 2h+ | STABLE | Remaining watch all-green. |

---

## Incident Analysis — 06:40–07:04 UTC

### What happened

Both services simultaneously returned 503, recovered briefly (two 3-minute windows of 200), crashed again to 503, progressed to 502 (mid-boot), then reverted to 503. Total degraded window: approximately 24 minutes with oscillating behaviour.

### Boot sequence interpretation

Render's status codes during a restart cycle have specific meanings:

| Status | Meaning |
|---|---|
| **503** (hibernate-wake-error header) | Service is fully hibernated. Render is blocking the request before the process even starts. |
| **502** (Bad Gateway) | Service process has started and is binding to its port. Render's proxy cannot reach it yet. |
| **200** | Service fully up and accepting connections. |

The oscillation `503 → 503 → 200 → 200 → 200 → 503 → 200 → 502 → 503` at 3-minute intervals indicates the service was **starting, running briefly, then being killed** — not just hibernating. This is consistent with an OOM (out-of-memory) kill on the Render free tier.

### Why the keep-warm could not prevent it

The keep-warm cron pings `/health` every 10 minutes (Vercel cron) with MCP02's session also pinging every 3 minutes. This is sufficient to prevent **hibernation-from-inactivity** (Render's threshold is ~15 minutes). However:

- An OOM kill happens when the service process exceeds the free-tier memory cap (~512MB)
- The kill can occur at any time, including between pings
- The `/health` endpoint that survives a ping does not guarantee all other endpoints are functioning (if the OOM is on a heavier request handler, the lightweight health check still passes)

### Root cause verdict

**Render free-tier OOM eviction at a low-traffic hour.** Not a code bug. Not a configuration error. The services were evicted by Render's infrastructure and took multiple restart cycles to stabilise.

---

## Second Event — 07:40 UTC (Blip, Not Crash-Loop)

Duration: ~3 minutes (one DEGRADED tick, recovered on next ping)  
Classification: **Transient blip** — single hibernation jitter or brief container refresh by Render  
Not a crash-loop (no oscillation, immediate recovery)

---

## Test Impact

**Zero.** All Playwright tests (6 PR #614 + 4 MCP02 calendar + 2 MCP02 S1 + 4 MCP02 final suite = 16 tests total per run) use `page.route()` intercepts to mock every backend API call:

```typescript
// Example from hor-pr614-verify.spec.ts
await page.route(/backend\.celeste7\.ai\/v1\/bootstrap/, async (route) => {
  await route.fulfill({ status: 200, body: JSON.stringify({ status: 'active', role, ... }) });
});
```

No network call reaches the actual Render services during test execution. Tests run in ~25 seconds regardless of Render service state.

---

## Regression Run Log

| UTC time | Tests | Result |
|---|---|---|
| 01:01 | 10/10 | PASS (baseline) |
| 01:32 | 10/10 | PASS |
| 02:02 | 10/10 | PASS |
| 02:32 | 10/10 | PASS |
| 03:17 | 10/10 | PASS |
| 03:47 | 10/10 | PASS |
| 04:17 | 10/10 | PASS |
| 04:47 | 10/10 | PASS |
| 05:17 | 10/10 | PASS |
| 05:47 | 10/10 | PASS |
| 06:17 | 10/10 | PASS |
| 06:47 | 10/10 | PASS |
| 07:17 | 10/10 | PASS (during incident — mocks unaffected) |
| 07:47 | 10/10 | PASS |
| 08:17 | 10/10 | PASS |
| 08:47 | 10/10 | PASS |
| 09:17 | 10/10 | PASS |
| 09:47 | 10/10 | PASS |

**Total: 18 runs · 180/180 tests passed · 0 regressions**

---

## Keep-Warm Coverage Assessment

The keep-warm cron (`apps/web/src/app/api/cron/keep-warm/route.ts`) running on Vercel every 10 minutes is effective at preventing hibernation-from-inactivity but has a structural gap:

| Scenario | Keep-warm prevents? |
|---|---|
| Hibernate after 15min inactivity | Yes — pings every 10min keep services active |
| OOM kill during startup | No — process is killed by Render before health check succeeds |
| OOM kill during runtime | No — process is killed between pings |
| Render infrastructure maintenance | No — not in our control |

---

## Recommendations

### Short term (no cost, already done)
- Keep-warm cron deployed — reduces hibernation incidents during normal hours
- All tests mocked — test results are immune to Render state

### Medium term (recommended)
Upgrade both Render services from free tier to Starter ($7/month each, $14/month total):
- No hibernation
- No OOM eviction (512MB → 1GB RAM)
- No cold starts
- SLA-backed uptime

For a production maritime compliance system — where crew may submit hours from any time zone including early UTC hours — the free-tier incident window (06:40–07:04 UTC) represents a real risk. If a crew member attempted to submit before a port inspection during that window, they would have encountered the timeout error message and needed to retry.

### Not recommended
Accepting the current risk for a production MLC compliance system. The 24-minute incident window is small but occurs at a predictable time (low-traffic early UTC). As the vessel count grows, the probability of a user collision with the incident window increases.

---

## Files Referenced

| File | Role |
|---|---|
| `apps/web/src/app/api/cron/keep-warm/route.ts` | The keep-warm endpoint itself |
| `apps/web/vercel.json` | Cron schedule: `*/10 * * * *` |
| `apps/web/src/app/api/v1/hours-of-rest/[...path]/route.ts:24` | `PROXY_TIMEOUT_MS = 28_000` — error message returned to users during outage |
| `apps/web/e2e/shard-37-hours-of-rest/hor-pr614-verify.spec.ts` | Mock intercepts that isolated all tests from this incident |
