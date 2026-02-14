'use client';

/**
 * SettingsSections - CelesteOS Settings Section Content
 *
 * Renders content for each settings section.
 * Fully tokenized, uses CSS custom properties.
 */

import React from 'react';
import { SettingsSection } from './SettingsConstants';
import {
  SettingsRow,
  FormGroup,
  UnifiedTextarea,
  SettingsButton,
  DateRangeButtonGroup,
} from './SettingsComponents';
import {
  languageOptions,
  appearanceOptions,
  dateRangeOptions,
  generationSourceOptions,
  messageTypeOptions,
} from './SettingsConstants';
import type { CelesteUser } from '@/contexts/AuthContext';

// ============================================================================
// TYPES
// ============================================================================

interface SectionContentProps {
  sectionId: SettingsSection;
  isMobile: boolean;
  displayName: string;
  onDisplayNameChange: (name: string) => void;
  language: string;
  setLanguage: (value: string) => void;
  appearance: string;
  setAppearance: (value: string) => void;
  dateRange: string;
  setDateRange: (value: string) => void;
  generationSource: string;
  setGenerationSource: (value: string) => void;
  messageType: string;
  setMessageType: (value: string) => void;
  messageContent: string;
  setMessageContent: (value: string) => void;
  logout?: () => Promise<void>;
  // These are now passed from parent component
  user?: CelesteUser | null;
  isExporting?: boolean;
  setIsExporting?: (value: boolean) => void;
  isSending?: boolean;
  setIsSending?: (value: boolean) => void;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function getLanguageLabel(value: string): string {
  const option = languageOptions.find((opt) => opt.value === value);
  return option ? option.label : 'English';
}

function getMessageTypeLabel(value: string, isMobile: boolean): string {
  if (value === '') return 'Select type...';
  if (value === 'issue' && isMobile) return 'Tech Issue';
  const option = messageTypeOptions.find((opt) => opt.value === value);
  return option ? option.label : 'Select type...';
}

// ============================================================================
// SECTION CONTENT RENDERER
// ============================================================================

export function renderSectionContent(props: SectionContentProps): React.ReactNode {
  const {
    sectionId,
    isMobile,
    displayName,
    onDisplayNameChange,
    language,
    setLanguage,
    appearance,
    setAppearance,
    dateRange,
    setDateRange,
    generationSource,
    setGenerationSource,
    messageType,
    setMessageType,
    messageContent,
    setMessageContent,
    logout,
    user,
    isExporting = false,
    setIsExporting,
    isSending = false,
    setIsSending,
  } = props;

  switch (sectionId) {
    case 'general':
      return (
        <div className="settings-card">
          <SettingsRow
            label="Display Name"
            value={displayName}
            isEditable={true}
            onChange={onDisplayNameChange}
            placeholder="Enter your display name"
            isMobile={isMobile}
          />

          <SettingsRow
            label="Department"
            value={user?.role?.replace('_', ' ') || 'Captain'}
            isEditable={false}
            isMobile={isMobile}
          />

          <SettingsRow
            label="Language"
            value={getLanguageLabel(language)}
            isEditable={true}
            onChange={setLanguage}
            type="select"
            options={languageOptions}
            isMobile={isMobile}
          />

          <SettingsRow
            label="Appearance"
            value={appearance}
            isEditable={true}
            onChange={setAppearance}
            type="select"
            options={appearanceOptions}
            isMobile={isMobile}
          />
        </div>
      );

    case 'connectors':
      return (
        <>
          <div className="settings-card">
            <SettingsRow
              label="Microsoft Outlook"
              value="Connected"
              isEditable={false}
              isMobile={isMobile}
            />

            <SettingsRow
              label={isMobile ? 'Email' : 'Email Address'}
              value={user?.email || 'john.doe@company.com'}
              isEditable={false}
              isMobile={isMobile}
            />

            <SettingsRow
              label="Organization"
              value={user?.yachtName || 'Acme Corporation'}
              isEditable={false}
              isMobile={isMobile}
            />

            <SettingsRow
              label="Last Synced"
              value={isMobile ? 'Jan 15, 2:45 PM' : 'January 15, 2024 at 2:45 PM'}
              isEditable={false}
              isMobile={isMobile}
            />
          </div>

          <div
            className="flex gap-3"
            style={{ marginTop: 'var(--celeste-spacing-8)' }}
          >
            <SettingsButton variant="secondary" style={{ width: '120px' }}>
              Disconnect
            </SettingsButton>
            <SettingsButton variant="primary" style={{ width: '120px' }}>
              Reconnect
            </SettingsButton>
          </div>
        </>
      );

    case 'handover':
      return (
        <>
          {/* Date Range */}
          <div className="settings-card mb-4">
            <div
              className="font-body text-celeste-text-title mb-3"
              style={{
                fontSize: 'var(--celeste-settings-label-size)',
                fontWeight: 'var(--celeste-settings-label-weight)',
              }}
            >
              Date Range
            </div>
            <DateRangeButtonGroup
              options={dateRangeOptions}
              value={dateRange}
              onChange={setDateRange}
            />
          </div>

          {/* Generation Source */}
          <div className="settings-card mb-8">
            <SettingsRow
              label="Generation Source"
              value={generationSource}
              isEditable={true}
              onChange={setGenerationSource}
              type="select"
              options={generationSourceOptions}
              isMobile={isMobile}
            />
          </div>

          <p
            className="font-body text-celeste-text-muted mb-8"
            style={{
              fontSize: 'var(--celeste-settings-label-size)',
              margin: '0 var(--celeste-settings-card-margin) var(--celeste-spacing-8)',
            }}
          >
            Export the work you've done, or what's happened across your team.
          </p>

          <div className="flex justify-center">
            <SettingsButton
              variant="primary"
              disabled={isExporting}
              onClick={async () => {
                setIsExporting?.(true);
                try {
                  // TODO: Implement export functionality
                  await new Promise((resolve) => setTimeout(resolve, 2000));
                  alert('Export request sent! Your report will be delivered to your email shortly.');
                } catch {
                  alert('Export failed. Please try again.');
                } finally {
                  setIsExporting?.(false);
                }
              }}
              style={{ width: '194px' }}
            >
              {isExporting ? 'Sending...' : 'Send to my email'}
            </SettingsButton>
          </div>
        </>
      );

    case 'account':
      return (
        <>
          <div className="settings-card">
            <SettingsRow
              label={isMobile ? 'Email' : 'Email Address'}
              value={user?.email || 'john.doe@company.com'}
              isEditable={false}
              isMobile={isMobile}
            />

            <SettingsRow
              label="Account Type"
              value="Yacht"
              isEditable={false}
              isMobile={isMobile}
            />

            <SettingsRow
              label="Member Since"
              value={isMobile ? 'Mar 15, 2023' : 'March 15, 2023'}
              isEditable={false}
              isMobile={isMobile}
            />
          </div>

          <div
            className="flex justify-center"
            style={{ marginTop: 'var(--celeste-spacing-8)' }}
          >
            <SettingsButton
              variant="primary"
              onClick={async () => {
                try {
                  if (logout) {
                    await logout();
                  } else {
                    // Fallback
                    localStorage.clear();
                    sessionStorage.clear();
                    window.location.reload();
                  }
                } catch (error) {
                  console.error('Logout error:', error);
                  localStorage.clear();
                  sessionStorage.clear();
                  window.location.reload();
                }
              }}
              style={{ width: '120px' }}
            >
              Logout
            </SettingsButton>
          </div>
        </>
      );

    case 'help-contact':
      return (
        <>
          {/* Help Header */}
          <div
            className="settings-card mb-8"
            style={{
              padding: '16px 20px',
            }}
          >
            <h3
              className="font-display text-celeste-text-title m-0 mb-2"
              style={{ fontSize: '16px', fontWeight: '600' }}
            >
              We're here to help
            </h3>
            <p
              className="font-body text-celeste-text-muted m-0"
              style={{ fontSize: '14px', lineHeight: '20px' }}
            >
              Replies usually within 24h. Urgent? Email support@celesteos.io
            </p>
          </div>

          {/* Contact Form */}
          <div className="settings-card mb-8">
            <SettingsRow
              label="Message Type"
              value={getMessageTypeLabel(messageType, isMobile)}
              isEditable={true}
              onChange={setMessageType}
              type="select"
              options={messageTypeOptions}
              isMobile={isMobile}
            />

            <SettingsRow
              label="Your Email"
              value={user?.email || 'user@company.com'}
              isEditable={false}
              isMobile={isMobile}
            />
          </div>

          <FormGroup
            label="Message"
            description="Please describe your feedback or issue in detail."
          >
            <UnifiedTextarea
              placeholder="Please describe your feedback or issue in detail..."
              rows={6}
              value={messageContent}
              onChange={(e) => setMessageContent(e.target.value)}
            />
          </FormGroup>

          <div className="flex justify-center">
            <SettingsButton
              variant="primary"
              disabled={!messageContent.trim() || !messageType || isSending}
              onClick={async () => {
                if (!messageContent.trim() || !messageType) {
                  alert('Please fill out all fields');
                  return;
                }
                setIsSending?.(true);
                try {
                  // TODO: Implement send functionality
                  await new Promise((resolve) => setTimeout(resolve, 2000));
                  alert('Message sent! We will get back to you soon.');
                  setMessageContent('');
                  setMessageType('');
                } catch {
                  // Fallback to mailto
                  const mailtoLink = `mailto:support@celesteos.io?subject=${encodeURIComponent(
                    messageType
                  )}&body=${encodeURIComponent(messageContent)}`;
                  window.location.href = mailtoLink;
                } finally {
                  setIsSending?.(false);
                }
              }}
              style={{ width: '168px' }}
            >
              {isSending ? 'Sending...' : 'Send Message'}
            </SettingsButton>
          </div>
        </>
      );

    default:
      return (
        <div className="font-body text-celeste-text-muted" style={{ fontSize: '16px' }}>
          Settings for this section will be available soon.
        </div>
      );
  }
}
