/**
 * Strict Reporter for Playwright Tests
 *
 * This reporter enforces strict testing policies:
 * 1. Fails the test run if ANY test is skipped
 * 2. Tracks console.error occurrences and fails accordingly
 * 3. Provides detailed pass/fail/skip counts
 *
 * PHILOSOPHY: Tests must be deterministic and complete.
 * Skipped tests indicate technical debt or incomplete coverage.
 * Console errors indicate potential runtime issues.
 */

import type {
  FullConfig,
  FullResult,
  Reporter,
  Suite,
  TestCase,
  TestResult,
} from '@playwright/test/reporter';

interface TestStats {
  passed: number;
  failed: number;
  skipped: number;
  flaky: number;
  timedOut: number;
  interrupted: number;
  consoleErrors: Map<string, string[]>; // testId -> error messages
}

class StrictReporter implements Reporter {
  private stats: TestStats = {
    passed: 0,
    failed: 0,
    skipped: 0,
    flaky: 0,
    timedOut: 0,
    interrupted: 0,
    consoleErrors: new Map(),
  };

  private skippedTests: string[] = [];
  private testsWithConsoleErrors: string[] = [];
  private startTime: number = 0;

  onBegin(config: FullConfig, suite: Suite): void {
    this.startTime = Date.now();
    const totalTests = this.countTests(suite);
    console.log('\n========================================');
    console.log('  STRICT MODE ENABLED');
    console.log('========================================');
    console.log(`  Total tests: ${totalTests}`);
    console.log('  Policy: No retries, no skips, no console errors');
    console.log('========================================\n');
  }

  onTestBegin(test: TestCase, result: TestResult): void {
    // Track test start - console errors will be collected via attachments
  }

  onTestEnd(test: TestCase, result: TestResult): void {
    const testTitle = `${test.parent.title} > ${test.title}`;

    switch (result.status) {
      case 'passed':
        this.stats.passed++;
        break;
      case 'failed':
        this.stats.failed++;
        break;
      case 'skipped':
        this.stats.skipped++;
        this.skippedTests.push(testTitle);
        break;
      case 'timedOut':
        this.stats.timedOut++;
        break;
      case 'interrupted':
        this.stats.interrupted++;
        break;
    }

    // Check for console errors in attachments
    const consoleErrorAttachment = result.attachments.find(
      (a) => a.name === 'console-errors'
    );
    if (consoleErrorAttachment && consoleErrorAttachment.body) {
      const errors = consoleErrorAttachment.body.toString();
      if (errors.trim()) {
        this.stats.consoleErrors.set(test.id, errors.split('\n'));
        this.testsWithConsoleErrors.push(testTitle);
      }
    }

    // Also check stderr for console errors
    if (result.stderr && result.stderr.length > 0) {
      const stderrContent = result.stderr.join('\n');
      if (stderrContent.includes('console.error') || stderrContent.includes('[ERROR]')) {
        if (!this.stats.consoleErrors.has(test.id)) {
          this.stats.consoleErrors.set(test.id, []);
        }
        this.stats.consoleErrors.get(test.id)!.push(stderrContent);
        if (!this.testsWithConsoleErrors.includes(testTitle)) {
          this.testsWithConsoleErrors.push(testTitle);
        }
      }
    }
  }

  async onEnd(result: FullResult): Promise<{ status?: FullResult['status'] } | undefined> {
    const duration = ((Date.now() - this.startTime) / 1000).toFixed(2);

    console.log('\n========================================');
    console.log('  STRICT TEST RESULTS');
    console.log('========================================');
    console.log(`  Duration: ${duration}s`);
    console.log('----------------------------------------');
    console.log(`  Passed:      ${this.stats.passed}`);
    console.log(`  Failed:      ${this.stats.failed}`);
    console.log(`  Skipped:     ${this.stats.skipped}`);
    console.log(`  Timed Out:   ${this.stats.timedOut}`);
    console.log(`  Interrupted: ${this.stats.interrupted}`);
    console.log(`  Console Errors: ${this.stats.consoleErrors.size} tests`);
    console.log('========================================\n');

    let shouldFail = false;
    const failureReasons: string[] = [];

    // Check for skipped tests
    if (this.stats.skipped > 0) {
      shouldFail = true;
      failureReasons.push(`STRICT MODE VIOLATION: ${this.stats.skipped} test(s) were skipped`);
      console.log('\n[STRICT] SKIPPED TESTS DETECTED:');
      this.skippedTests.forEach((test) => {
        console.log(`  - ${test}`);
      });
      console.log('\nSkipped tests are not allowed in strict mode.');
      console.log('Either fix the test or remove it from the suite.\n');
    }

    // Check for console errors
    if (this.testsWithConsoleErrors.length > 0) {
      shouldFail = true;
      failureReasons.push(`STRICT MODE VIOLATION: ${this.testsWithConsoleErrors.length} test(s) had console errors`);
      console.log('\n[STRICT] CONSOLE ERRORS DETECTED:');
      this.testsWithConsoleErrors.forEach((test) => {
        console.log(`  - ${test}`);
      });
      console.log('\nConsole errors must be resolved before tests can pass.\n');
    }

    // Check for actual test failures
    if (this.stats.failed > 0 || this.stats.timedOut > 0) {
      shouldFail = true;
      failureReasons.push(`${this.stats.failed} test(s) failed, ${this.stats.timedOut} timed out`);
    }

    if (shouldFail) {
      console.log('\n========================================');
      console.log('  STRICT MODE: TEST RUN FAILED');
      console.log('========================================');
      failureReasons.forEach((reason) => {
        console.log(`  - ${reason}`);
      });
      console.log('========================================\n');
      return { status: 'failed' };
    }

    console.log('\n========================================');
    console.log('  STRICT MODE: ALL CHECKS PASSED');
    console.log('========================================\n');
    return { status: 'passed' };
  }

  private countTests(suite: Suite): number {
    let count = suite.tests.length;
    for (const child of suite.suites) {
      count += this.countTests(child);
    }
    return count;
  }

  // Utility to get stats for external consumption
  getStats(): TestStats {
    return { ...this.stats };
  }
}

export default StrictReporter;
