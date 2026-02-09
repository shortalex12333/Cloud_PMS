const { Client } = require('pg');

async function fixForeignKeys() {
  const client = new Client({
    host: 'aws-0-us-west-1.pooler.supabase.com',
    port: 5432,
    database: 'postgres',
    user: 'postgres.vzsohavtuotocgrfkfyd',
    password: '@-Ei-9Pa.uENn6g',
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();
    console.log('✓ Connected to database\n');

    // Drop incorrect constraint
    console.log('1. Dropping incorrect finalized_by constraint...');
    await client.query('ALTER TABLE handover_items DROP CONSTRAINT IF EXISTS handover_items_finalized_by_fkey;');
    console.log('✅ Constraint dropped\n');

    // Add correct constraint
    console.log('2. Adding correct constraint...');
    await client.query('ALTER TABLE handover_items ADD CONSTRAINT handover_items_finalized_by_fkey FOREIGN KEY (finalized_by) REFERENCES auth_users_profiles(id);');
    console.log('✅ Constraint added\n');

    // Verify
    console.log('3. Verifying constraints...');
    const result = await client.query(`
      SELECT
          conname AS constraint_name,
          conrelid::regclass AS table_name,
          confrelid::regclass AS referenced_table,
          a.attname AS column_name,
          af.attname AS referenced_column
      FROM pg_constraint c
      JOIN pg_attribute a ON a.attnum = ANY(c.conkey) AND a.attrelid = c.conrelid
      JOIN pg_attribute af ON af.attnum = ANY(c.confkey) AND af.attrelid = c.confrelid
      WHERE conrelid = 'handover_items'::regclass
        AND confrelid IS NOT NULL
      ORDER BY conname;
    `);

    console.log('Foreign key constraints on handover_items:');
    result.rows.forEach(row => {
      console.log(`  - ${row.constraint_name}: ${row.column_name} → ${row.referenced_table}.${row.referenced_column}`);
    });

  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  } finally {
    await client.end();
  }
}

fixForeignKeys();
