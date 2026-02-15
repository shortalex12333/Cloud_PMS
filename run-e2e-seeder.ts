#!/usr/bin/env tsx
import { seedE2ETestData } from './tests/e2e/helpers/seed-e2e-data';

async function main() {
  console.log('🌱 Starting E2E test data seeding...');
  const result = await seedE2ETestData();

  if (result.success) {
    console.log('✅ Seeding completed successfully');
    console.log(`   Seeded ${result.seeded.length} entities:`);
    result.seeded.forEach(item => console.log(`   - ${item}`));
    process.exit(0);
  } else {
    console.error('❌ Seeding failed with errors:');
    result.errors.forEach(error => console.error(`   - ${error}`));
    process.exit(1);
  }
}

main().catch(error => {
  console.error('💥 Seeding script crashed:', error);
  process.exit(1);
});
