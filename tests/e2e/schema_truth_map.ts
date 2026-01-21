/**
 * Schema Truth Map Generator
 *
 * Compares actual database tables with code-referenced tables.
 * Outputs a mismatch report.
 */

import { createClient } from '@supabase/supabase-js';
import * as fs from 'fs';
import * as path from 'path';

// Load env vars
const TENANT_SUPABASE_URL = process.env.TENANT_SUPABASE_URL || 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_SERVICE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY || '';

if (!TENANT_SERVICE_KEY) {
  console.error('ERROR: TENANT_SUPABASE_SERVICE_ROLE_KEY not set');
  process.exit(1);
}

const supabase = createClient(TENANT_SUPABASE_URL, TENANT_SERVICE_KEY);

async function getActualTables(): Promise<string[]> {
  // Query information_schema to get all tables in the public schema
  const { data, error } = await supabase.rpc('exec_sql', {
    query: `
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
      ORDER BY table_name
    `
  });

  if (error) {
    // RPC might not exist, try alternative approach
    console.log('RPC not available, trying direct query...');

    // Alternative: Try to get tables by probing known ones
    const knownTables = [
      // PMS tables
      'pms_equipment',
      'pms_faults',
      'pms_work_orders',
      'pms_parts',
      'pms_maintenance_schedules',
      'pms_handover',
      'pms_handover_items',
      'pms_handover_sections',
      'pms_checklist_templates',
      'pms_task_checklists',
      'pms_equipment_history',
      // Documents
      'documents',
      'document_chunks',
      'search_document_chunks',
      // Email
      'email_watchers',
      'email_threads',
      'email_messages',
      'email_attachments',
      'email_links',
      // Auth
      'auth_microsoft_tokens',
      'oauth_tokens',
      'user_integrations',
      // Compliance
      'compliance_records',
      'certificates',
      // Inventory
      'inventory',
      'v_inventory',
      // Purchasing
      'purchase_orders',
      'purchase_requests',
      'suppliers',
      // Work
      'work_order_notes',
      'work_order_photos',
      'task_assignments',
      // Ledger
      'ledger_events',
      'audit_log',
    ];

    const existingTables: string[] = [];
    for (const table of knownTables) {
      const { error: testError } = await supabase.from(table).select('*').limit(0);
      if (!testError) {
        existingTables.push(table);
      }
    }
    return existingTables.sort();
  }

  return (data || []).map((row: any) => row.table_name).sort();
}

function getCodeReferencedTables(codebaseRoot: string): string[] {
  // Use grep to find .from('table_name') patterns
  const { execSync } = require('child_process');

  try {
    // Search for Supabase .from('table') patterns
    const grepResult = execSync(
      `grep -roh "from(['\"]\\([^'\"]*\\)['\"])" "${codebaseRoot}/apps" 2>/dev/null | sort | uniq`,
      { encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024 }
    );

    const tables = new Set<string>();
    const fromPattern = /from\(['"]([^'"]+)['"]\)/g;

    let match;
    while ((match = fromPattern.exec(grepResult)) !== null) {
      const tableName = match[1];
      // Filter out non-table names (like 'local', test mocks, etc.)
      if (tableName && !tableName.includes('/') && !tableName.startsWith('_')) {
        tables.add(tableName);
      }
    }

    // Also search for explicit table references in Python
    const pythonGrepResult = execSync(
      `grep -roh "table(['\"]\\([^'\"]*\\)['\"])" "${codebaseRoot}/apps" 2>/dev/null | sort | uniq || true`,
      { encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024 }
    );

    const tablePattern = /table\(['"]([^'"]+)['"]\)/g;
    while ((match = tablePattern.exec(pythonGrepResult)) !== null) {
      const tableName = match[1];
      if (tableName && !tableName.includes('/') && !tableName.startsWith('_')) {
        tables.add(tableName);
      }
    }

    return Array.from(tables).sort();
  } catch (e) {
    console.error('Error running grep:', e);
    return [];
  }
}

async function main() {
  console.log('=== SCHEMA TRUTH MAP ===\n');
  console.log('Tenant DB:', TENANT_SUPABASE_URL);

  // Get actual tables
  console.log('\n1. Fetching actual database tables...');
  const actualTables = await getActualTables();
  console.log(`   Found ${actualTables.length} tables in database`);

  // Get code-referenced tables
  console.log('\n2. Scanning codebase for table references...');
  const codebaseRoot = '/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS';
  const codeReferencedTables = getCodeReferencedTables(codebaseRoot);
  console.log(`   Found ${codeReferencedTables.length} tables referenced in code`);

  // Find mismatches
  const actualSet = new Set(actualTables);
  const codeSet = new Set(codeReferencedTables);

  const inDbNotCode = actualTables.filter(t => !codeSet.has(t));
  const inCodeNotDb = codeReferencedTables.filter(t => !actualSet.has(t));
  const inBoth = actualTables.filter(t => codeSet.has(t));

  // Generate report
  const report = {
    generated_at: new Date().toISOString(),
    tenant_db: TENANT_SUPABASE_URL,
    summary: {
      actual_tables: actualTables.length,
      code_referenced_tables: codeReferencedTables.length,
      in_both: inBoth.length,
      in_db_not_code: inDbNotCode.length,
      in_code_not_db: inCodeNotDb.length,
    },
    tables: {
      in_database: actualTables,
      in_code: codeReferencedTables,
      in_both: inBoth,
      in_db_not_code: inDbNotCode,
      in_code_not_db: inCodeNotDb,
    },
    mismatches: inCodeNotDb.map(t => ({
      table: t,
      issue: 'Referenced in code but does not exist in database',
      action: 'Create migration or remove code reference',
    })),
  };

  // Output report
  console.log('\n=== MISMATCH REPORT ===\n');
  console.log('Summary:');
  console.log(`  Tables in DB:       ${report.summary.actual_tables}`);
  console.log(`  Tables in code:     ${report.summary.code_referenced_tables}`);
  console.log(`  In both:            ${report.summary.in_both}`);
  console.log(`  In DB, not code:    ${report.summary.in_db_not_code}`);
  console.log(`  In code, not DB:    ${report.summary.in_code_not_db}`);

  if (inCodeNotDb.length > 0) {
    console.log('\n⚠️  Tables referenced in code but MISSING from database:');
    inCodeNotDb.forEach(t => console.log(`   - ${t}`));
  } else {
    console.log('\n✅ All code-referenced tables exist in database');
  }

  if (inDbNotCode.length > 0) {
    console.log('\n📋 Tables in database but not referenced in app code:');
    inDbNotCode.forEach(t => console.log(`   - ${t}`));
  }

  // Write report to file
  const outputPath = path.join(codebaseRoot, 'verification_handoff/evidence/SCHEMA_TRUTH_MAP.json');
  fs.writeFileSync(outputPath, JSON.stringify(report, null, 2));
  console.log(`\n📝 Full report written to: ${outputPath}`);

  // Write markdown summary
  const mdPath = path.join(codebaseRoot, 'verification_handoff/evidence/SCHEMA_TRUTH_MAP.md');
  let md = `# Schema Truth Map

Generated: ${report.generated_at}
Tenant DB: ${report.tenant_db}

## Summary

| Metric | Count |
|--------|-------|
| Tables in Database | ${report.summary.actual_tables} |
| Tables in Code | ${report.summary.code_referenced_tables} |
| In Both | ${report.summary.in_both} |
| In DB, not code | ${report.summary.in_db_not_code} |
| In Code, not DB | ${report.summary.in_code_not_db} |

## Mismatches (Code references DB doesn't have)

`;

  if (inCodeNotDb.length > 0) {
    md += '| Table | Issue | Action |\n|-------|-------|--------|\n';
    report.mismatches.forEach(m => {
      md += `| ${m.table} | ${m.issue} | ${m.action} |\n`;
    });
  } else {
    md += '✅ **All code-referenced tables exist in the database.**\n';
  }

  md += `
## All Tables

### In Database (${actualTables.length})
${actualTables.map(t => `- ${t}`).join('\n')}

### In Code (${codeReferencedTables.length})
${codeReferencedTables.map(t => `- ${t}`).join('\n')}
`;

  fs.writeFileSync(mdPath, md);
  console.log(`📝 Markdown report written to: ${mdPath}`);
}

main().catch(console.error);
