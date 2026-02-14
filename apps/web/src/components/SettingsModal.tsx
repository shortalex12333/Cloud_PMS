'use client';

/**
 * SettingsModal - CelesteOS Settings Entry Point
 *
 * Wrapper component that renders the new tokenized Settings panel.
 * Maintains backward compatibility with existing usage.
 */

import { Settings } from './settings';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  isMobile?: boolean;
}

export default function SettingsModal({ isOpen, onClose, isMobile }: SettingsModalProps) {
  return <Settings isOpen={isOpen} onClose={onClose} isMobile={isMobile} />;
}
