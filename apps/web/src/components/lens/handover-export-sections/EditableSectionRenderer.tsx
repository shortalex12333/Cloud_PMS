'use client';

import { useState } from 'react';
import { GhostButton } from '@/components/ui/GhostButton';

interface SectionItem {
  id: string;
  content: string;
  entity_type?: string;
  entity_id?: string;
  priority?: 'critical' | 'action' | 'fyi';
}

interface Section {
  id: string;
  title: string;
  content: string;
  items: SectionItem[];
  is_critical: boolean;
  order: number;
}

interface EditableSectionRendererProps {
  sections: Section[];
  onSectionsChange: (sections: Section[]) => void;
  mode: 'edit' | 'review';
}

export function EditableSectionRenderer({
  sections,
  onSectionsChange,
  mode
}: EditableSectionRendererProps) {
  const isEditable = mode === 'edit';

  const updateSection = (sectionId: string, updates: Partial<Section>) => {
    if (!isEditable) return;
    onSectionsChange(
      sections.map(s => s.id === sectionId ? { ...s, ...updates } : s)
    );
  };

  const addSection = () => {
    if (!isEditable) return;
    const newSection: Section = {
      id: `section-${Date.now()}`,
      title: 'New Section',
      content: '',
      items: [],
      is_critical: false,
      order: sections.length
    };
    onSectionsChange([...sections, newSection]);
  };

  const removeSection = (sectionId: string) => {
    if (!isEditable) return;
    onSectionsChange(sections.filter(s => s.id !== sectionId));
  };

  const moveSection = (sectionId: string, direction: 'up' | 'down') => {
    if (!isEditable) return;
    const index = sections.findIndex(s => s.id === sectionId);
    if (index === -1) return;
    if (direction === 'up' && index === 0) return;
    if (direction === 'down' && index === sections.length - 1) return;

    const newSections = [...sections];
    const swapIndex = direction === 'up' ? index - 1 : index + 1;
    [newSections[index], newSections[swapIndex]] = [newSections[swapIndex], newSections[index]];

    // Update order values
    newSections.forEach((s, i) => { s.order = i; });
    onSectionsChange(newSections);
  };

  const addItem = (sectionId: string) => {
    if (!isEditable) return;
    const section = sections.find(s => s.id === sectionId);
    if (!section) return;

    const newItem: SectionItem = {
      id: `item-${Date.now()}`,
      content: '',
      priority: 'fyi'
    };

    updateSection(sectionId, {
      items: [...section.items, newItem]
    });
  };

  const updateItem = (sectionId: string, itemId: string, content: string) => {
    if (!isEditable) return;
    const section = sections.find(s => s.id === sectionId);
    if (!section) return;

    updateSection(sectionId, {
      items: section.items.map(i =>
        i.id === itemId ? { ...i, content } : i
      )
    });
  };

  const removeItem = (sectionId: string, itemId: string) => {
    if (!isEditable) return;
    const section = sections.find(s => s.id === sectionId);
    if (!section) return;

    updateSection(sectionId, {
      items: section.items.filter(i => i.id !== itemId)
    });
  };

  const getPriorityBadgeColor = (priority?: string) => {
    switch (priority) {
      case 'critical': return 'bg-status-critical/20 text-status-critical';
      case 'action': return 'bg-status-warning/20 text-status-warning';
      case 'fyi': return 'bg-surface-secondary text-txt-secondary';
      default: return 'bg-surface-secondary text-txt-secondary';
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {sections
        .sort((a, b) => a.order - b.order)
        .map((section) => (
          <div
            key={section.id}
            className="bg-surface-primary rounded-md overflow-hidden border border-surface-border"
          >
            {/* Section header */}
            <div className="flex items-center justify-between h-11 px-4 bg-surface-primary border-b border-surface-border">
              <div className="flex items-center gap-2 flex-1">
                {isEditable ? (
                  <input
                    type="text"
                    value={section.title}
                    onChange={(e) => updateSection(section.id, { title: e.target.value })}
                    className="bg-transparent text-[14px] font-semibold text-txt-primary border-b border-transparent hover:border-surface-border focus:border-brand-interactive outline-none w-full"
                  />
                ) : (
                  <h2 className="text-[14px] font-semibold text-txt-primary">{section.title}</h2>
                )}
                {section.is_critical && (
                  <span className="px-2 py-0.5 typo-meta rounded bg-status-critical/20 text-status-critical font-medium">
                    CRITICAL
                  </span>
                )}
              </div>

              {/* Section controls (edit mode only) */}
              {isEditable && (
                <div className="flex gap-1 ml-2">
                  <GhostButton onClick={() => moveSection(section.id, 'up')}>↑</GhostButton>
                  <GhostButton onClick={() => moveSection(section.id, 'down')}>↓</GhostButton>
                  <GhostButton onClick={() => removeSection(section.id)}>Remove</GhostButton>
                </div>
              )}
            </div>

            {/* Section content */}
            <div className="px-4 pb-4 pt-3">
              {/* Critical checkbox (edit mode only) */}
              {isEditable && (
                <label className="flex items-center gap-2 typo-body text-txt-secondary mb-3">
                  <input
                    type="checkbox"
                    checked={section.is_critical}
                    onChange={(e) => updateSection(section.id, { is_critical: e.target.checked })}
                    className="rounded"
                  />
                  Mark as Critical
                </label>
              )}

              {/* Section body text */}
              {isEditable ? (
                <textarea
                  value={section.content}
                  onChange={(e) => updateSection(section.id, { content: e.target.value })}
                  className="w-full min-h-[80px] p-2 bg-surface-secondary rounded border border-surface-border resize-y text-txt-primary"
                  placeholder="Section content..."
                />
              ) : (
                section.content && (
                  <p className="text-txt-primary whitespace-pre-wrap">{section.content}</p>
                )
              )}

              {/* Section items */}
              <div className="mt-4 flex flex-col gap-2">
                {section.items.map((item) => (
                  <div key={item.id} className="flex items-start gap-2 p-2 bg-surface-secondary rounded">
                    <span className={`px-2 py-0.5 typo-meta rounded flex-shrink-0 ${getPriorityBadgeColor(item.priority)}`}>
                      {item.priority || 'fyi'}
                    </span>
                    {isEditable ? (
                      <>
                        <input
                          type="text"
                          value={item.content}
                          onChange={(e) => updateItem(section.id, item.id, e.target.value)}
                          className="flex-1 bg-transparent border-b border-transparent hover:border-surface-border focus:border-brand-interactive outline-none text-txt-primary"
                          placeholder="Item content..."
                        />
                        <button
                          onClick={() => removeItem(section.id, item.id)}
                          className="text-txt-tertiary hover:text-status-critical flex-shrink-0"
                        >
                          ×
                        </button>
                      </>
                    ) : (
                      <span className="flex-1 text-txt-primary">{item.content}</span>
                    )}
                  </div>
                ))}

                {isEditable && (
                  <button
                    onClick={() => addItem(section.id)}
                    className="self-start typo-body text-brand-interactive hover:underline"
                  >
                    + Add item
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}

      {/* Add section button (edit mode only) */}
      {isEditable && (
        <button
          onClick={addSection}
          className="p-4 border-2 border-dashed border-surface-border rounded-lg text-txt-secondary hover:border-brand-interactive hover:text-brand-interactive transition-colors"
        >
          + Add Section
        </button>
      )}
    </div>
  );
}
