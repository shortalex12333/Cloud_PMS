/**
 * Extract REAL entity IDs from lens CSV exports
 *
 * Usage: npx tsx e2e/scripts/extract-real-ids.ts
 */

import * as fs from 'fs';
import * as path from 'path';

const LENS_DATA_DIR = '/Users/celeste7/Downloads/New Folder With Items';

interface LensRecord {
  id: string;
  object_type: string;
  object_id: string;  // This is the REAL entity UUID
  yacht_id: string;
  payload: string;    // JSON with entity details
  filters: string;    // JSON with status and other filters
}

interface ExtractedEntity {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  filters: Record<string, unknown>;
}

function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      result.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}

function extractFromCSV(filename: string, limit = 10): ExtractedEntity[] {
  const filepath = path.join(LENS_DATA_DIR, filename);
  if (!fs.existsSync(filepath)) {
    console.log(`  ⚠️ File not found: ${filename}`);
    return [];
  }

  const content = fs.readFileSync(filepath, 'utf-8');
  const lines = content.split('\n');
  const headers = parseCSVLine(lines[0]);

  const objectIdIdx = headers.indexOf('object_id');
  const objectTypeIdx = headers.indexOf('object_type');
  const payloadIdx = headers.indexOf('payload');
  const filtersIdx = headers.indexOf('filters');

  const entities: ExtractedEntity[] = [];

  for (let i = 1; i < Math.min(lines.length, limit + 1); i++) {
    if (!lines[i].trim()) continue;

    try {
      const cols = parseCSVLine(lines[i]);
      const objectId = cols[objectIdIdx];
      const objectType = cols[objectTypeIdx];

      let payload = {};
      let filters = {};

      try {
        const payloadStr = cols[payloadIdx]?.replace(/^"|"$/g, '').replace(/""/g, '"');
        if (payloadStr) payload = JSON.parse(payloadStr);
      } catch {}

      try {
        const filtersStr = cols[filtersIdx]?.replace(/^"|"$/g, '').replace(/""/g, '"');
        if (filtersStr) filters = JSON.parse(filtersStr);
      } catch {}

      if (objectId && objectId.match(/^[0-9a-f-]{36}$/i)) {
        entities.push({
          id: objectId,
          type: objectType,
          payload,
          filters,
        });
      }
    } catch (e) {
      // Skip malformed lines
    }
  }

  return entities;
}

function main() {
  console.log('🔍 Extracting REAL entity IDs from lens exports...\n');

  const lensFiles = {
    certificate: 'certificate.csv',
    document: 'document.csv',
    fault: 'fault.csv',
    inventory: 'inventory.csv',
    parts: 'parts.csv',
    receiving: 'receiving.csv',
    shopping_list: 'shopping_list.csv',
    work_order: 'work_order.csv',
    work_order_note: 'work_order_note.csv',
  };

  const allEntities: Record<string, ExtractedEntity[]> = {};

  for (const [domain, file] of Object.entries(lensFiles)) {
    console.log(`📄 Processing ${domain}...`);
    const entities = extractFromCSV(file, 20);
    allEntities[domain] = entities;
    console.log(`   Found ${entities.length} entities`);

    // Show sample with status
    if (entities.length > 0) {
      const sample = entities.slice(0, 3);
      for (const e of sample) {
        const status = (e.filters as any)?.status || (e.payload as any)?.status || 'unknown';
        const name = (e.payload as any)?.name || (e.payload as any)?.title || (e.payload as any)?.part_number || '';
        console.log(`     - ${e.id.substring(0, 8)}... [${status}] ${name.substring(0, 30)}`);
      }
    }
  }

  // Generate test-context-real.ts
  const output: Record<string, Record<string, string>> = {};

  // Certificates - group by status
  const certs = allEntities.certificate || [];
  output.CERTIFICATE_IDS = {};
  for (const c of certs) {
    const status = (c.filters as any)?.status || 'active';
    const key = `${status.toUpperCase()}_${Object.keys(output.CERTIFICATE_IDS).length + 1}`;
    output.CERTIFICATE_IDS[key] = c.id;
    if (Object.keys(output.CERTIFICATE_IDS).length >= 5) break;
  }

  // Documents
  const docs = allEntities.document || [];
  output.DOCUMENT_IDS = {};
  for (const d of docs.slice(0, 5)) {
    const key = `DOC_${Object.keys(output.DOCUMENT_IDS).length + 1}`;
    output.DOCUMENT_IDS[key] = d.id;
  }

  // Faults - group by status
  const faults = allEntities.fault || [];
  output.FAULT_IDS = {};
  const faultsByStatus: Record<string, string[]> = {};
  for (const f of faults) {
    const status = (f.filters as any)?.status || 'open';
    if (!faultsByStatus[status]) faultsByStatus[status] = [];
    faultsByStatus[status].push(f.id);
  }
  for (const [status, ids] of Object.entries(faultsByStatus)) {
    output.FAULT_IDS[`${status.toUpperCase()}_1`] = ids[0];
    if (ids[1]) output.FAULT_IDS[`${status.toUpperCase()}_2`] = ids[1];
  }

  // Work Orders - group by status
  const workOrders = allEntities.work_order || [];
  output.WORK_ORDER_IDS = {};
  const woByStatus: Record<string, string[]> = {};
  for (const wo of workOrders) {
    const status = (wo.filters as any)?.status || (wo.payload as any)?.status || 'draft';
    if (!woByStatus[status]) woByStatus[status] = [];
    woByStatus[status].push(wo.id);
  }
  for (const [status, ids] of Object.entries(woByStatus)) {
    output.WORK_ORDER_IDS[`${status.toUpperCase()}_1`] = ids[0];
    if (ids[1]) output.WORK_ORDER_IDS[`${status.toUpperCase()}_2`] = ids[1];
  }

  // Parts
  const parts = allEntities.parts || [];
  output.PART_IDS = {};
  for (const p of parts.slice(0, 5)) {
    const name = (p.payload as any)?.part_number || `PART_${Object.keys(output.PART_IDS).length + 1}`;
    output.PART_IDS[name.replace(/[^A-Z0-9]/gi, '_').toUpperCase()] = p.id;
  }

  // Receiving - group by status
  const receiving = allEntities.receiving || [];
  output.RECEIVING_IDS = {};
  const recvByStatus: Record<string, string[]> = {};
  for (const r of receiving) {
    const status = (r.filters as any)?.status || 'draft';
    if (!recvByStatus[status]) recvByStatus[status] = [];
    recvByStatus[status].push(r.id);
  }
  for (const [status, ids] of Object.entries(recvByStatus)) {
    output.RECEIVING_IDS[`${status.toUpperCase()}_1`] = ids[0];
  }

  // Shopping List - group by status
  const shoppingList = allEntities.shopping_list || [];
  output.SHOPPING_LIST_IDS = {};
  const slByStatus: Record<string, string[]> = {};
  for (const s of shoppingList) {
    const status = (s.filters as any)?.status || 'pending';
    if (!slByStatus[status]) slByStatus[status] = [];
    slByStatus[status].push(s.id);
  }
  for (const [status, ids] of Object.entries(slByStatus)) {
    output.SHOPPING_LIST_IDS[`${status.toUpperCase()}_1`] = ids[0];
  }

  console.log('\n📊 EXTRACTED REAL IDs:\n');
  console.log(JSON.stringify(output, null, 2));

  // Write to file
  const outputPath = path.join(process.cwd(), 'e2e/shard-12-action-coverage/real-lens-ids.json');
  fs.writeFileSync(outputPath, JSON.stringify(output, null, 2));
  console.log(`\n✅ Written to: ${outputPath}`);
}

main();
