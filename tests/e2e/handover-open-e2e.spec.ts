import { test, expect } from '@playwright/test';

test.use({ storageState: 'test-results/.auth-states/crew-state.json' });

const VALID_TOKEN = 'eyJhbGciOiJIUzI1NiIsImtpZCI6InYxIiwidHlwIjoiSldUIn0.eyJ0eXBlIjoid29ya19vcmRlciIsImlkIjoiYjM2MjM4ZGEtYjBmYS00ODE1LTg4M2MtMGJlNjFmYzE5MGQwIiwieWFjaHRfaWQiOiI4NWZlMTExOS1iMDRjLTQxYWMtODBmMS04MjlkMjMzMjI1OTgiLCJleHAiOjE3NzAzOTUwNzUsIm5vbmNlIjoiYjZjNWUyM2IwNDAyOGFiMTAyODkxNjE4NWI3NTU5NjAiLCJzY29wZSI6InZpZXciLCJ2IjoxfQ.OOTWKPzTLYyyK3m5ekmP1nuyLuLOXVnO-3uKrWMxLXA';

test('Handover link full E2E', async ({ page }) => {
  // Capture console logs
  page.on('console', msg => console.log('BROWSER:', msg.text()));
  
  // Capture network requests
  page.on('response', async response => {
    if (response.url().includes('resolve')) {
      console.log('RESOLVE API:', response.status(), await response.text().catch(() => 'no body'));
    }
  });

  console.log('1. Going to /open...');
  await page.goto(`https://app.celeste7.ai/open?t=${VALID_TOKEN}`);
  
  // Wait for processing
  await page.waitForTimeout(8000);
  
  console.log('2. Final URL:', page.url());
  
  // Check sessionStorage
  const stored = await page.evaluate(() => sessionStorage.getItem('handover_open_result'));
  console.log('3. SessionStorage result:', stored);
  
  await page.screenshot({ path: 'test-results/handover-final.png', fullPage: true });
  
  // Should redirect to /app
  expect(page.url()).toMatch(/app/);
  console.log('TEST PASSED');
});
