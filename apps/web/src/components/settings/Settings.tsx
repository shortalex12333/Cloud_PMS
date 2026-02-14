'use client';

/**
 * Settings - CelesteOS Settings Modal
 *
 * Apple System Preferences-inspired settings panel.
 * Two layouts: Desktop (sidebar + content) and Mobile (accordion).
 * Fully tokenized - all styles via CSS custom properties.
 */

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SettingsSection, settingsMenuItems } from './SettingsConstants';
import { SectionHeader, MobileSectionHeader } from './SettingsComponents';
import { renderSectionContent } from './SettingsSections';
import { useAuth } from '@/hooks/useAuth';

// ============================================================================
// TYPES
// ============================================================================

interface SettingsProps {
  isOpen: boolean;
  onClose: () => void;
  isMobile?: boolean;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function Settings({ isOpen, onClose, isMobile = false }: SettingsProps) {
  const { user, logout } = useAuth();

  // State
  const [activeSection, setActiveSection] = useState<SettingsSection>('general');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['general']));
  const [displayName, setDisplayName] = useState(user?.displayName || '');
  const [language, setLanguage] = useState('en');
  const [appearance, setAppearance] = useState('light');
  const [dateRange, setDateRange] = useState('last-30-days');
  const [generationSource, setGenerationSource] = useState('both');
  const [messageType, setMessageType] = useState('');
  const [messageContent, setMessageContent] = useState('');
  const [isExporting, setIsExporting] = useState(false);
  const [isSending, setIsSending] = useState(false);

  // Theme handling
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('celeste_theme');
      if (saved) setAppearance(saved);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const root = document.documentElement;
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (appearance === 'dark' || (appearance === 'system' && systemDark)) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('celeste_theme', appearance);
  }, [appearance]);

  // Sync display name with user
  useEffect(() => {
    if (user?.displayName) {
      setDisplayName(user.displayName);
    }
  }, [user?.displayName]);

  // Escape key handler
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const sectionContentProps = {
    isMobile,
    displayName,
    onDisplayNameChange: setDisplayName,
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
    isExporting,
    setIsExporting,
    isSending,
    setIsSending,
  };

  // ============================================================================
  // MOBILE LAYOUT
  // ============================================================================

  if (isMobile) {
    return (
      <div className="fixed inset-0 z-[10000] flex items-center justify-center">
        {/* Backdrop */}
        <div
          className="absolute inset-0 transition-opacity duration-celeste-slow"
          style={{ backgroundColor: `rgba(var(--celeste-backdrop-color), 0.6)` }}
          onClick={onClose}
        />

        {/* Mobile Modal */}
        <div
          className="relative w-full h-full overflow-hidden z-10 spotlight-panel"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between"
            style={{
              padding: 'var(--celeste-spacing-4)',
              borderBottom: '1px solid var(--celeste-settings-header-border)',
              background: 'var(--celeste-settings-header-bg)',
            }}
          >
            <h1
              className="font-display text-celeste-text-title m-0"
              style={{ fontSize: '18px', fontWeight: '500' }}
            >
              Settings
            </h1>
            <button
              onClick={onClose}
              className={cn(
                'p-[var(--celeste-spacing-2)] rounded-celeste-md',
                'border border-celeste-border-subtle',
                'text-celeste-text-muted',
                'hover:bg-celeste-bg-tertiary hover:text-celeste-text-primary',
                'transition-colors duration-celeste-fast',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent'
              )}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content - Accordion */}
          <div
            className="flex-1 overflow-y-auto spotlight-scrollbar"
            style={{
              padding: 'var(--celeste-spacing-4)',
              height: 'calc(100vh - var(--celeste-settings-header-height))',
              background: 'var(--celeste-settings-content-bg)',
            }}
          >
            {settingsMenuItems.map((section) => {
              const isExpanded = expandedSections.has(section.id);

              return (
                <div key={section.id} className="mb-[var(--celeste-spacing-3)]">
                  <MobileSectionHeader
                    section={section}
                    isExpanded={isExpanded}
                    onToggle={() => toggleSection(section.id)}
                  />

                  {isExpanded && (
                    <div
                      className="animate-celeste-fade-in"
                      style={{
                        background: 'var(--celeste-settings-card-bg)',
                        border: '1px solid var(--celeste-settings-card-border)',
                        borderTop: 'none',
                        borderRadius: '0 0 var(--celeste-settings-card-radius) var(--celeste-settings-card-radius)',
                        padding: 'var(--celeste-spacing-4)',
                        marginBottom: 'var(--celeste-spacing-3)',
                      }}
                    >
                      {renderSectionContent({
                        sectionId: section.id,
                        ...sectionContentProps,
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // ============================================================================
  // DESKTOP LAYOUT
  // ============================================================================

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 transition-opacity duration-celeste-slow backdrop-blur-md"
        style={{ backgroundColor: `rgba(var(--celeste-backdrop-color), var(--celeste-backdrop-opacity))` }}
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="relative overflow-hidden z-10 settings-panel"
        style={{
          width: 'var(--celeste-settings-width)',
          maxWidth: '95vw',
          height: 'var(--celeste-settings-height)',
          maxHeight: '90vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between"
          style={{
            padding: 'var(--celeste-spacing-6)',
            borderBottom: '1px solid var(--celeste-settings-header-border)',
            background: 'var(--celeste-settings-header-bg)',
          }}
        >
          <h1
            className="font-display text-celeste-text-title m-0"
            style={{ fontSize: '18px', fontWeight: '500' }}
          >
            Settings
          </h1>
          <button
            onClick={onClose}
            className={cn(
              'p-[var(--celeste-spacing-2)] rounded-celeste-md',
              'border border-celeste-border-subtle',
              'text-celeste-text-muted',
              'hover:bg-celeste-bg-tertiary hover:text-celeste-text-primary',
              'transition-colors duration-celeste-fast',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent'
            )}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div
          className="flex overflow-hidden"
          style={{ height: 'calc(100% - var(--celeste-settings-header-height))' }}
        >
          {/* Sidebar */}
          <div className="settings-sidebar overflow-y-auto spotlight-scrollbar">
            <div style={{ padding: '16px' }}>
              {settingsMenuItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeSection === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveSection(item.id)}
                    className={cn(
                      'settings-sidebar-item w-full text-left mb-2',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-celeste-accent'
                    )}
                    data-active={isActive}
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Content Area */}
          <div
            className="flex-1 overflow-y-auto spotlight-scrollbar"
            style={{
              background: 'var(--celeste-settings-content-bg)',
            }}
          >
            <div style={{ padding: '32px' }}>
              <SectionHeader
                title={settingsMenuItems.find((item) => item.id === activeSection)?.label || 'Settings'}
                isMobile={isMobile}
              />
              {renderSectionContent({
                sectionId: activeSection,
                ...sectionContentProps,
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
