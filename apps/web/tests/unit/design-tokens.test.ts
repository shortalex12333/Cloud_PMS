/**
 * Design Token Verification
 * Phase 00-01: Verify tokens.css contains correct values per CLAUDE.md specification
 *
 * These tests verify the token FILE contains the correct values.
 * CSS custom property runtime rendering is verified via Playwright E2E.
 */

import { readFileSync } from 'fs';
import { join } from 'path';

const tokensPath = join(__dirname, '../../src/styles/tokens.css');
const tokensContent = readFileSync(tokensPath, 'utf-8');

describe('Design Tokens — tokens.css', () => {
  describe('File exists and has content', () => {
    it('tokens.css exists and is non-empty', () => {
      expect(tokensContent.length).toBeGreaterThan(100);
    });
  });

  describe('Dark theme tokens (default / :root)', () => {
    it('has --surface-base: #111111 (dark app background)', () => {
      expect(tokensContent).toContain('--surface-base: #111111');
    });

    it('has --surface-primary: #171717 (dark cards)', () => {
      expect(tokensContent).toContain('--surface-primary: #171717');
    });

    it('has --surface-elevated: #1E1E1E (dark modals)', () => {
      expect(tokensContent).toContain('--surface-elevated: #1E1E1E');
    });

    it('has --text-primary: #ECECEC (dark main text)', () => {
      expect(tokensContent).toContain('--text-primary: #ECECEC');
    });

    it('has dark shadow tokens', () => {
      expect(tokensContent).toContain('--shadow-sm: 0 2px 8px rgba(0,0,0,0.3)');
      expect(tokensContent).toContain('--shadow-md: 0 8px 24px rgba(0,0,0,0.4)');
      expect(tokensContent).toContain('--shadow-lg: 0 16px 48px rgba(0,0,0,0.5)');
    });

    it('has dark glass tokens', () => {
      expect(tokensContent).toContain('--glass-bg: rgba(17,17,17,0.75)');
      expect(tokensContent).toContain('--glass-blur: blur(20px)');
    });
  });

  describe('Light theme tokens ([data-theme="light"])', () => {
    // Extract light theme section: from the opening brace of [data-theme="light"] { to its closing }
    // The selector appears twice in the file: once in a comment, once as actual CSS.
    // Use a regex to find the actual ruleset.
    const lightMatch = tokensContent.match(/\[data-theme="light"\]\s*\{([^}]+)\}/);
    const lightSection = lightMatch ? lightMatch[1] : '';

    it('has [data-theme="light"] selector as CSS ruleset', () => {
      expect(lightMatch).not.toBeNull();
    });

    it('has --surface-base: #FFFFFF (light app background)', () => {
      expect(lightSection).toContain('--surface-base: #FFFFFF');
    });

    it('has --surface-border: #E7E7E7 (ChatGPT exact border color)', () => {
      expect(lightSection).toContain('--surface-border: #E7E7E7');
    });

    it('has --text-primary: #0D0D0D (light main text)', () => {
      expect(lightSection).toContain('--text-primary: #0D0D0D');
    });

    it('has light shadow tokens (barely visible)', () => {
      expect(lightSection).toContain('--shadow-sm: 0 1px 3px rgba(0,0,0,0.06)');
    });

    it('has light glass tokens', () => {
      expect(lightSection).toContain('--glass-bg: rgba(255,255,255,0.75)');
    });
  });

  describe('Shared brand tokens', () => {
    it('has --brand-ambient: #3A7C9D (teal logo color)', () => {
      expect(tokensContent).toContain('--brand-ambient: #3A7C9D');
    });

    it('has --brand-interactive: #2B8FB3 (teal buttons/links)', () => {
      expect(tokensContent).toContain('--brand-interactive: #2B8FB3');
    });

    it('has --brand-hover: #239AB8', () => {
      expect(tokensContent).toContain('--brand-hover: #239AB8');
    });
  });

  describe('Status tokens', () => {
    it('has --status-critical: #E5484D', () => {
      expect(tokensContent).toContain('--status-critical: #E5484D');
    });

    it('has --status-warning: #F5A623', () => {
      expect(tokensContent).toContain('--status-warning: #F5A623');
    });

    it('has --status-success: #30A46C', () => {
      expect(tokensContent).toContain('--status-success: #30A46C');
    });

    it('has status background tokens', () => {
      expect(tokensContent).toContain('--status-critical-bg');
      expect(tokensContent).toContain('--status-warning-bg');
      expect(tokensContent).toContain('--status-success-bg');
      expect(tokensContent).toContain('--status-neutral-bg');
    });
  });

  describe('Spacing tokens (4px grid)', () => {
    it('has --space-1: 4px through --space-20: 80px', () => {
      expect(tokensContent).toContain('--space-1: 4px');
      expect(tokensContent).toContain('--space-2: 8px');
      expect(tokensContent).toContain('--space-4: 16px');
      expect(tokensContent).toContain('--space-8: 32px');
      expect(tokensContent).toContain('--space-20: 80px');
    });
  });

  describe('Radius tokens', () => {
    it('has all radius tokens', () => {
      expect(tokensContent).toContain('--radius-sm: 8px');
      expect(tokensContent).toContain('--radius-md: 12px');
      expect(tokensContent).toContain('--radius-lg: 16px');
      expect(tokensContent).toContain('--radius-xl: 24px');
      expect(tokensContent).toContain('--radius-full: 9999px');
    });
  });

  describe('Z-index tokens', () => {
    it('has --z-sticky through --z-toast', () => {
      expect(tokensContent).toContain('--z-sticky: 10');
      expect(tokensContent).toContain('--z-header: 20');
      expect(tokensContent).toContain('--z-modal: 40');
      expect(tokensContent).toContain('--z-toast: 60');
    });
  });

  describe('Transition tokens', () => {
    it('has --ease-out cubic-bezier', () => {
      expect(tokensContent).toContain('--ease-out: cubic-bezier(0.16, 1, 0.3, 1)');
    });

    it('has duration tokens', () => {
      expect(tokensContent).toContain('--duration-fast: 120ms');
      expect(tokensContent).toContain('--duration-normal: 200ms');
      expect(tokensContent).toContain('--duration-slow: 300ms');
    });
  });
});
