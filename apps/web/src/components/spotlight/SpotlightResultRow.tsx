'use client';

/**
 * SpotlightResultRow — Raycast-style
 * Icon-left, full-row selection, ↵ kbd hint on selected.
 */

import React from 'react';
import {
  AlertTriangle, ClipboardList, Package, FileText, Mail,
  Award, ArrowRightLeft, ShoppingCart, Receipt, Clock,
  Settings, Shield, MoreHorizontal, type LucideIcon,
} from 'lucide-react';

// ── Entity type → icon ──────────────────────────────────────────────────────

const ENTITY_TYPE_ICONS: Record<string, LucideIcon> = {
  work_order:             ClipboardList,
  fault:                  AlertTriangle,
  equipment:              Settings,
  part:                   Package,
  inventory:              Package,
  document:               FileText,
  search_document_chunks: FileText,
  email_thread:           Mail,
  email_threads:          Mail,
  certificate:            Award,
  warranty:               Shield,
  shopping_list:          ShoppingCart,
  shopping_list_item:     ShoppingCart,
  receiving:              ArrowRightLeft,
  purchase_order:         Receipt,
  hours_of_rest:          Clock,
};

function getEntityIcon(type: string): LucideIcon {
  if (ENTITY_TYPE_ICONS[type]) return ENTITY_TYPE_ICONS[type];
  if (type.includes('fault'))       return AlertTriangle;
  if (type.includes('work_order'))  return ClipboardList;
  if (type.includes('equipment'))   return Settings;
  if (type.includes('part'))        return Package;
  if (type.includes('inventory'))   return Package;
  if (type.includes('certificate')) return Award;
  if (type.includes('warranty'))    return Shield;
  if (type.includes('shopping'))    return ShoppingCart;
  if (type.includes('receiving'))   return ArrowRightLeft;
  if (type.includes('purchase'))    return Receipt;
  if (type.includes('hours'))       return Clock;
  if (type.includes('document'))    return FileText;
  if (type.includes('email'))       return Mail;
  return MoreHorizontal;
}

// ── Types ───────────────────────────────────────────────────────────────────

interface SpotlightResult {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  snippet?: string;
  icon?: string;
  metadata?: Record<string, unknown>;
}

interface SpotlightResultRowProps {
  result: SpotlightResult;
  isSelected: boolean;
  index: number;
  onClick?: () => void;
  onDoubleClick?: () => void;
  isTopMatch?: boolean;
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function renderSnippetWithBold(text: string): React.ReactNode {
  const parts = text.split(/\*\*([^*]+)\*\*/g);
  return parts.map((part, index) =>
    index % 2 === 1
      ? <strong key={index} className="font-semibold text-txt-primary">{part}</strong>
      : part
  );
}

// ── Component ────────────────────────────────────────────────────────────────

export default function SpotlightResultRow({
  result,
  isSelected,
  index,
  onClick,
  onDoubleClick,
  isTopMatch = false,
}: SpotlightResultRowProps) {
  const Icon = getEntityIcon(result.type);

  return (
    <div
      data-index={index}
      data-testid="search-result-item"
      data-selected={isSelected ? 'true' : 'false'}
      data-top-match={isTopMatch ? 'true' : 'false'}
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      className="spotlight-item"
    >
      {/* Entity type icon */}
      <Icon className="spotlight-item-icon" aria-hidden="true" />

      {/* Text content */}
      <div className="flex flex-col gap-0.5 flex-1 min-w-0">
        <p className="text-body font-medium leading-snug truncate text-txt-primary">
          {result.title}
        </p>
        {result.snippet && (
          <p
            className="text-caption font-normal leading-snug line-clamp-2 text-txt-secondary"
            data-testid="search-result-snippet"
          >
            {renderSnippetWithBold(result.snippet)}
          </p>
        )}
        {result.subtitle && !result.snippet && (
          <p className="text-caption font-normal leading-snug truncate text-txt-tertiary">
            {result.subtitle}
          </p>
        )}
      </div>

      {/* kbd hint — CSS controls visibility on selected state */}
      <div className="spotlight-item-hint" aria-hidden="true">
        <span className="spotlight-kbd">↵</span>
      </div>
    </div>
  );
}
