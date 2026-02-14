/**
 * CelesteOS Settings - Public API
 *
 * Export all settings components and types for external use.
 */

// Main Component
export { default as Settings } from './Settings';

// Constants & Types
export {
  type SettingsSection,
  type SettingsMenuItem,
  type SelectOption,
  settingsMenuItems,
  languageOptions,
  appearanceOptions,
  dateRangeOptions,
  generationSourceOptions,
  accountScopeOptions,
  messageTypeOptions,
} from './SettingsConstants';

// UI Components
export {
  SectionHeader,
  FormGroup,
  SettingsRow,
  SwitchRow,
  UnifiedTextarea,
  MobileSectionHeader,
  SettingsButton,
  DateRangeButtonGroup,
} from './SettingsComponents';

// Section Content Renderer
export { renderSectionContent } from './SettingsSections';
