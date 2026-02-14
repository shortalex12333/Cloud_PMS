'use client';

/**
 * SettingsConstants - CelesteOS Settings Configuration
 *
 * Centralized configuration for settings sections, options, and menu items.
 * All values configurable from single location.
 */

import { Settings as SettingsIcon, Plug, ArrowUpDown, User, HelpCircle } from 'lucide-react';

// ============================================================================
// TYPES
// ============================================================================

export type SettingsSection = 'general' | 'connectors' | 'handover' | 'account' | 'help-contact';

export interface SettingsMenuItem {
  id: SettingsSection;
  label: string;
  icon: typeof SettingsIcon;
}

export interface SelectOption {
  value: string;
  label: string;
}

// ============================================================================
// MENU ITEMS
// ============================================================================

export const settingsMenuItems: SettingsMenuItem[] = [
  { id: 'general', label: 'General', icon: SettingsIcon },
  { id: 'connectors', label: 'Connectors', icon: Plug },
  { id: 'handover', label: 'Handover', icon: ArrowUpDown },
  { id: 'account', label: 'Account', icon: User },
  { id: 'help-contact', label: 'Help & Contact', icon: HelpCircle },
];

// ============================================================================
// SELECT OPTIONS
// ============================================================================

export const languageOptions: SelectOption[] = [
  { value: 'auto', label: 'Auto-detect' },
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'ru', label: 'Russian' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
  { value: 'zh', label: 'Chinese (Simplified)' },
];

export const appearanceOptions: SelectOption[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
];

export const dateRangeOptions: SelectOption[] = [
  { value: 'today', label: 'Today' },
  { value: 'last-7-days', label: 'Last 7 days' },
  { value: 'last-30-days', label: 'Last 30 days' },
  { value: 'last-90-days', label: 'Last 90 days' },
  { value: 'last-year', label: 'Last year' },
  { value: 'all-time', label: 'All time' },
];

export const generationSourceOptions: SelectOption[] = [
  { value: 'outlook', label: 'Outlook' },
  { value: 'my-notes', label: 'My Notes' },
  { value: 'both', label: 'Both' },
];

export const accountScopeOptions: SelectOption[] = [
  { value: 'this-account', label: 'This account' },
  { value: 'entire-faults', label: 'Entire faults' },
];

export const messageTypeOptions: SelectOption[] = [
  { value: '', label: 'Select type...' },
  { value: 'feedback', label: 'Feedback' },
  { value: 'issue', label: 'Technical Issue' },
  { value: 'feature', label: 'Feature Request' },
  { value: 'billing', label: 'Billing Question' },
];
