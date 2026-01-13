/**
 * Playwright Global Teardown
 *
 * Runs once after all tests
 */

import * as fs from 'fs';
import * as path from 'path';

async function globalTeardown() {
  console.log('\n========================================');
  console.log('Global Teardown: Starting');
  console.log('========================================\n');

  // Clean up auth state
  const authStatePath = path.join(process.cwd(), 'test-results', '.auth-state.json');
  if (fs.existsSync(authStatePath)) {
    fs.unlinkSync(authStatePath);
    console.log('Cleaned up auth state.');
  }

  // Generate artifacts summary
  const artifactsDir = path.join(process.cwd(), 'test-results', 'artifacts');
  if (fs.existsSync(artifactsDir)) {
    const artifacts = getAllFiles(artifactsDir);
    console.log(`\nArtifacts generated: ${artifacts.length} files`);

    // Group by test
    const byTest: Record<string, string[]> = {};
    for (const file of artifacts) {
      const rel = path.relative(artifactsDir, file);
      const testName = rel.split(path.sep)[0];
      if (!byTest[testName]) {
        byTest[testName] = [];
      }
      byTest[testName].push(path.basename(file));
    }

    console.log('\nArtifacts by test:');
    for (const [test, files] of Object.entries(byTest)) {
      console.log(`  ${test}: ${files.join(', ')}`);
    }
  }

  console.log('\n========================================');
  console.log('Global Teardown: Complete');
  console.log('========================================\n');
}

function getAllFiles(dir: string): string[] {
  const files: string[] = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...getAllFiles(fullPath));
    } else {
      files.push(fullPath);
    }
  }

  return files;
}

export default globalTeardown;
