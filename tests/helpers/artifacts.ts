/**
 * Artifacts Helper
 *
 * Captures and saves test evidence: requests, responses, DB state, screenshots
 */

import * as fs from 'fs';
import * as path from 'path';
import { Page } from '@playwright/test';

const ARTIFACTS_DIR = path.join(process.cwd(), 'test-results', 'artifacts');

/**
 * Ensure artifacts directory exists
 */
function ensureArtifactsDir(subDir?: string): string {
  const dir = subDir ? path.join(ARTIFACTS_DIR, subDir) : ARTIFACTS_DIR;
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

/**
 * Save JSON artifact
 */
export function saveArtifact(
  filename: string,
  data: any,
  subDir?: string
): string {
  const dir = ensureArtifactsDir(subDir);
  const filePath = path.join(dir, filename);

  // Ensure parent directory exists
  fs.mkdirSync(path.dirname(filePath), { recursive: true });

  const content = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  fs.writeFileSync(filePath, content);

  console.log(`  Artifact saved: ${filePath} (${content.length} bytes)`);
  return filePath;
}

/**
 * Save HTTP request artifact
 */
export function saveRequest(
  testName: string,
  request: {
    method: string;
    url: string;
    headers?: Record<string, string>;
    body?: any;
  }
): string {
  return saveArtifact(
    'request.json',
    {
      timestamp: new Date().toISOString(),
      method: request.method,
      url: request.url,
      headers: sanitizeHeaders(request.headers || {}),
      body: request.body,
    },
    testName
  );
}

/**
 * Save HTTP response artifact
 */
export function saveResponse(
  testName: string,
  response: {
    status?: number;
    statusText?: string;
    headers?: Record<string, string>;
    body?: any;
    [key: string]: any; // Allow additional properties for test metadata
  }
): string {
  return saveArtifact(
    'response.json',
    {
      timestamp: new Date().toISOString(),
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
      body: response.body,
    },
    testName
  );
}

/**
 * Save DB state (before or after)
 */
export function saveDbState(
  testName: string,
  state: 'before' | 'after',
  data: any
): string {
  return saveArtifact(`db_${state}.json`, data, testName);
}

/**
 * Save audit log entry
 */
export function saveAuditLog(testName: string, data: any): string {
  return saveArtifact('audit_log.json', data, testName);
}

/**
 * Take and save screenshot
 */
export async function saveScreenshot(
  page: Page,
  testName: string,
  name: string = 'screenshot'
): Promise<string> {
  const dir = ensureArtifactsDir(testName);
  const filePath = path.join(dir, `${name}.png`);

  await page.screenshot({ path: filePath, fullPage: true });

  console.log(`  Screenshot saved: ${filePath}`);
  return filePath;
}

/**
 * Save console logs
 */
export function saveConsoleLogs(
  testName: string,
  logs: Array<{ type: string; text: string; timestamp: string }>
): string {
  return saveArtifact('console_logs.json', logs, testName);
}

/**
 * Save network HAR (if available)
 */
export function saveHar(testName: string, har: any): string {
  return saveArtifact('network.har', har, testName);
}

/**
 * Create a test evidence bundle
 */
export function createEvidenceBundle(
  testName: string,
  evidence: {
    request?: any;
    response?: any;
    dbBefore?: any;
    dbAfter?: any;
    auditLog?: any;
    consoleLogs?: any[];
    assertions?: Array<{ name: string; passed: boolean; message?: string }>;
    [key: string]: any; // Allow additional evidence properties
  }
): string {
  const bundle = {
    testName,
    timestamp: new Date().toISOString(),
    evidence,
    summary: {
      hasRequest: !!evidence.request,
      hasResponse: !!evidence.response,
      hasDbBefore: !!evidence.dbBefore,
      hasDbAfter: !!evidence.dbAfter,
      hasAuditLog: !!evidence.auditLog,
      assertionsPassed: evidence.assertions?.every((a) => a.passed) ?? true,
    },
  };

  return saveArtifact('evidence_bundle.json', bundle, testName);
}

/**
 * Sanitize headers (remove sensitive values)
 */
function sanitizeHeaders(headers: Record<string, string>): Record<string, string> {
  const sanitized: Record<string, string> = {};

  for (const [key, value] of Object.entries(headers)) {
    if (key.toLowerCase() === 'authorization') {
      // Mask the token but keep the type
      const parts = value.split(' ');
      if (parts.length === 2) {
        sanitized[key] = `${parts[0]} ${parts[1].substring(0, 10)}...`;
      } else {
        sanitized[key] = '***';
      }
    } else if (key.toLowerCase().includes('key') || key.toLowerCase().includes('secret')) {
      sanitized[key] = '***';
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
}

/**
 * Get path to artifacts directory for a test
 */
export function getArtifactsPath(testName: string): string {
  return ensureArtifactsDir(testName);
}

/**
 * Check if artifacts exist for a test
 */
export function hasArtifacts(testName: string): boolean {
  const dir = path.join(ARTIFACTS_DIR, testName);
  if (!fs.existsSync(dir)) {
    return false;
  }

  const files = fs.readdirSync(dir);
  return files.length > 0;
}

/**
 * List all artifacts for a test
 */
export function listArtifacts(testName: string): string[] {
  const dir = path.join(ARTIFACTS_DIR, testName);
  if (!fs.existsSync(dir)) {
    return [];
  }

  return fs.readdirSync(dir).map((f) => path.join(dir, f));
}

/**
 * Clear artifacts for a test (use before re-running)
 */
export function clearArtifacts(testName: string): void {
  const dir = path.join(ARTIFACTS_DIR, testName);
  if (fs.existsSync(dir)) {
    fs.rmSync(dir, { recursive: true });
  }
}
