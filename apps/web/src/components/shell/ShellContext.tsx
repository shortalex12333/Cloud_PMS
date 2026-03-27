'use client';

/**
 * ShellContext — shared state between AppShell and page content
 *
 * Provides:
 * - Active domain (derived from pathname)
 * - Tier 2 search query (debounced, from Subbar input)
 * - Active filter chip
 * - Navigation helpers
 *
 * Pages can optionally consume this context to integrate with
 * the shell's search and filter controls.
 */

import * as React from 'react';
import type { DomainId } from './Sidebar';

interface ShellState {
  activeDomain: DomainId;
  searchQuery: string;
  debouncedQuery: string;
  activeChip: string;
  setSearchQuery: (q: string) => void;
  setActiveChip: (chip: string) => void;
}

const ShellContext = React.createContext<ShellState | null>(null);

export function ShellProvider({
  activeDomain,
  children,
}: {
  activeDomain: DomainId;
  children: React.ReactNode;
}) {
  const [searchQuery, setSearchQuery] = React.useState('');
  const [debouncedQuery, setDebouncedQuery] = React.useState('');
  const [activeChip, setActiveChip] = React.useState('All');

  // Reset search and chip when domain changes
  React.useEffect(() => {
    setSearchQuery('');
    setDebouncedQuery('');
    setActiveChip('All');
  }, [activeDomain]);

  // Debounce search query — 300ms to avoid excessive API calls per REVIEWER01
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const value = React.useMemo(
    () => ({
      activeDomain,
      searchQuery,
      debouncedQuery,
      activeChip,
      setSearchQuery,
      setActiveChip,
    }),
    [activeDomain, searchQuery, debouncedQuery, activeChip]
  );

  return (
    <ShellContext.Provider value={value}>
      {children}
    </ShellContext.Provider>
  );
}

export function useShellContext(): ShellState {
  const ctx = React.useContext(ShellContext);
  if (!ctx) {
    // Graceful fallback for pages rendered outside the shell
    return {
      activeDomain: 'surface',
      searchQuery: '',
      debouncedQuery: '',
      activeChip: 'All',
      setSearchQuery: () => {},
      setActiveChip: () => {},
    };
  }
  return ctx;
}
