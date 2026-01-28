/**
 * DATABASE RELATIONSHIPS DISCOVERY
 * Purpose: Map all tables, columns, foreign keys, constraints for PMS system
 */

const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
require('dotenv').config({ path: '.env.e2e' });

const TENANT_SUPABASE_URL = process.env.TENANT_SUPABASE_URL;
const TENANT_SUPABASE_SERVICE_ROLE_KEY = process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY;

const supabase = createClient(TENANT_SUPABASE_URL, TENANT_SUPABASE_SERVICE_ROLE_KEY);

const TEST_YACHT_ID = '85fe1119-b04c-41ac-80f1-829d23322598';

async function discoverSchema() {
  console.log('\n🔍 DISCOVERING DATABASE SCHEMA\n');
  console.log('='.repeat(80));

  // List of known PMS tables
  const pmsTables = [
    'pms_work_orders',
    'pms_faults',
    'pms_equipment',
    'pms_parts',
    'pms_maintenance_schedules',
    'pms_audit_log',
    'pms_inventory_movements',
    'pms_work_order_notes',
    'pms_fault_notes',
    'pms_equipment_notes',
    'pms_documents',
    'pms_checklists',
    'pms_checklist_items',
    'pms_suppliers',
    'pms_orders',
    'pms_order_items'
  ];

  const relationships = {};

  for (const tableName of pmsTables) {
    console.log(`\n📊 Table: ${tableName}`);
    console.log('-'.repeat(80));

    try {
      // Get sample row to infer schema
      const { data, error } = await supabase
        .from(tableName)
        .select('*')
        .limit(1);

      if (error) {
        console.log(`   ❌ Error: ${error.message}`);
        continue;
      }

      if (!data || data.length === 0) {
        console.log(`   ⚠️  No data found`);
        // Still try to get schema from empty table
        const { data: emptyData, error: emptyError } = await supabase
          .from(tableName)
          .select('*')
          .limit(0);

        if (!emptyError) {
          console.log(`   ✅ Table exists (empty)`);
        }
        continue;
      }

      const sampleRow = data[0];
      const columns = Object.keys(sampleRow);

      console.log(`   ✅ Columns (${columns.length}):`);

      relationships[tableName] = {
        columns: {},
        foreignKeys: [],
        indexes: []
      };

      // Analyze each column
      for (const col of columns) {
        const value = sampleRow[col];
        const type = typeof value;
        const isNull = value === null;

        let inferredType = 'unknown';
        if (isNull) {
          inferredType = 'null';
        } else if (type === 'string' && value.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i)) {
          inferredType = 'uuid';
        } else if (type === 'string' && value.match(/^\d{4}-\d{2}-\d{2}T/)) {
          inferredType = 'timestamp';
        } else if (type === 'number') {
          inferredType = 'numeric';
        } else if (type === 'boolean') {
          inferredType = 'boolean';
        } else if (type === 'object') {
          inferredType = Array.isArray(value) ? 'array' : 'jsonb';
        } else if (type === 'string') {
          inferredType = 'text';
        }

        relationships[tableName].columns[col] = {
          type: inferredType,
          nullable: isNull,
          sample: isNull ? null : (type === 'object' ? JSON.stringify(value).substring(0, 50) + '...' : String(value).substring(0, 50))
        };

        // Detect foreign keys by naming convention
        if (col.endsWith('_id') && inferredType === 'uuid') {
          const referencedTable = col.replace('_id', '');
          relationships[tableName].foreignKeys.push({
            column: col,
            likelyReferences: `pms_${referencedTable}s` // or other naming patterns
          });
        }

        console.log(`      - ${col}: ${inferredType}${isNull ? ' (nullable)' : ''}`);
      }

      // Identify likely foreign keys
      if (relationships[tableName].foreignKeys.length > 0) {
        console.log(`\n   🔗 Likely Foreign Keys:`);
        for (const fk of relationships[tableName].foreignKeys) {
          console.log(`      - ${fk.column} → ${fk.likelyReferences}`);
        }
      }

    } catch (err) {
      console.log(`   ❌ Error: ${err.message}`);
    }
  }

  console.log('\n\n' + '='.repeat(80));
  console.log('📝 WRITING RELATIONSHIPS TO FILE\n');

  // Write to file
  const output = {
    discoveredAt: new Date().toISOString(),
    yachtId: TEST_YACHT_ID,
    tables: relationships
  };

  fs.writeFileSync(
    '_VERIFICATION/DATABASE_RELATIONSHIPS.json',
    JSON.stringify(output, null, 2)
  );

  console.log('✅ Written to: _VERIFICATION/DATABASE_RELATIONSHIPS.json\n');

  return relationships;
}

async function generateMarkdown(relationships) {
  console.log('📄 GENERATING MARKDOWN DOCUMENTATION\n');

  let markdown = `# PMS Database Relationships\n\n`;
  markdown += `**Generated:** ${new Date().toISOString()}\n`;
  markdown += `**Source:** Live database schema discovery\n\n`;
  markdown += `---\n\n`;

  markdown += `## Overview\n\n`;
  markdown += `Total Tables Discovered: ${Object.keys(relationships).length}\n\n`;
  markdown += `---\n\n`;

  for (const [tableName, schema] of Object.entries(relationships)) {
    markdown += `## Table: \`${tableName}\`\n\n`;
    markdown += `**Columns:** ${Object.keys(schema.columns).length}\n\n`;

    markdown += `### Schema\n\n`;
    markdown += `| Column | Type | Nullable | Sample Value |\n`;
    markdown += `|--------|------|----------|-------------|\n`;

    for (const [colName, colInfo] of Object.entries(schema.columns)) {
      const sample = colInfo.sample === null ? 'NULL' : `\`${colInfo.sample}\``;
      markdown += `| ${colName} | ${colInfo.type} | ${colInfo.nullable ? '✅' : '❌'} | ${sample} |\n`;
    }

    if (schema.foreignKeys.length > 0) {
      markdown += `\n### Foreign Keys\n\n`;
      for (const fk of schema.foreignKeys) {
        markdown += `- \`${fk.column}\` → likely references \`${fk.likelyReferences}\`\n`;
      }
    }

    markdown += `\n---\n\n`;
  }

  fs.writeFileSync(
    '_VERIFICATION/DATABASE_RELATIONSHIPS.md',
    markdown
  );

  console.log('✅ Written to: _VERIFICATION/DATABASE_RELATIONSHIPS.md\n');
}

async function main() {
  const relationships = await discoverSchema();
  await generateMarkdown(relationships);

  console.log('\n✅ DATABASE RELATIONSHIP DISCOVERY COMPLETE\n');
}

main().catch(console.error);
