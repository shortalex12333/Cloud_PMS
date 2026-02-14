'use client';

/**
 * SettingsModal - CelesteOS Settings Entry Point
 *
 * Wrapper component that renders the frosted glass Settings panel.
 * Matches c.os.4.1 reference design.
 */

import { Settings } from './settings';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  return <Settings isOpen={isOpen} onClose={onClose} />;
}
