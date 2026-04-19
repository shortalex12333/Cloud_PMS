'use client';

/**
 * TimeSlider — 24-hour WORK period input
 *
 * User draws WORK blocks (amber). Blank slider = no work = 24h rest (valid).
 * onChange emits work_periods. Use invertToRestPeriods() if you need rest_periods.
 *
 * Interaction:
 * - Click empty track → creates a new 1-hour work block
 * - Drag left/right handles → resize
 * - Drag block body → move
 * - "×" → remove block
 */

import * as React from 'react';

// ── Types ───────────────────────────────────────────────────────────────────

export interface RestPeriod {
  start: string; // "HH:MM"
  end: string;   // "HH:MM"
}

/** Invert work_periods into rest_periods (24h complement). Empty work = [{00:00–24:00}]. */
export function invertToRestPeriods(workPeriods: RestPeriod[]): RestPeriod[] {
  if (!workPeriods.length) return [{ start: '00:00', end: '24:00' }];
  const sorted = [...workPeriods].sort((a, b) => a.start.localeCompare(b.start));
  const gaps: RestPeriod[] = [];
  if (sorted[0].start > '00:00') gaps.push({ start: '00:00', end: sorted[0].start });
  for (let i = 0; i < sorted.length - 1; i++) {
    if (sorted[i].end < sorted[i + 1].start) {
      gaps.push({ start: sorted[i].end, end: sorted[i + 1].start });
    }
  }
  const last = sorted[sorted.length - 1];
  if (last.end < '24:00') gaps.push({ start: last.end, end: '24:00' });
  return gaps;
}

interface Block {
  id: string;
  startMin: number; // 0–1440
  endMin: number;   // 0–1440
}

interface TimeSliderProps {
  /** Initial work periods from saved/submitted data */
  value?: RestPeriod[];
  /** Called every time blocks change — emits work_periods */
  onChange: (periods: RestPeriod[]) => void;
  /** If true: read-only (submitted day, no editing) */
  readOnly?: boolean;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + (m || 0);
}

function toHHMM(minutes: number): string {
  const clamped = Math.max(0, Math.min(1440, Math.round(minutes)));
  const h = Math.floor(clamped / 60) % 24;
  const m = clamped % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function snapToQuarter(minutes: number): number {
  return Math.round(minutes / 15) * 15;
}

function periodsFromBlocks(blocks: Block[]): RestPeriod[] {
  return blocks
    .filter(b => b.endMin > b.startMin)
    .sort((a, b) => a.startMin - b.startMin)
    .map(b => ({ start: toHHMM(b.startMin), end: toHHMM(b.endMin) }));
}

/** Clamp overlapping blocks so they meet but never overlap. */
function resolveOverlaps(blocks: Block[]): Block[] {
  const sorted = [...blocks].sort((a, b) => a.startMin - b.startMin);
  for (let i = 1; i < sorted.length; i++) {
    const prev = sorted[i - 1];
    const curr = sorted[i];
    if (curr.startMin < prev.endMin) {
      sorted[i] = { ...curr, startMin: prev.endMin };
    }
  }
  return sorted.filter(b => b.endMin > b.startMin);
}

// ── Component ────────────────────────────────────────────────────────────────

export function TimeSlider({ value, onChange, readOnly = false }: TimeSliderProps) {
  const trackRef = React.useRef<HTMLDivElement>(null);

  const [blocks, setBlocks] = React.useState<Block[]>(() => {
    if (!value?.length) return [];
    return value.map(p => ({
      id: Math.random().toString(36).slice(2),
      startMin: toMinutes(p.start),
      endMin: toMinutes(p.end),
    }));
  });

  // Sync when value prop changes (e.g. template applied)
  React.useEffect(() => {
    if (!value) return;
    setBlocks(value.map(p => ({
      id: Math.random().toString(36).slice(2),
      startMin: toMinutes(p.start),
      endMin: toMinutes(p.end),
    })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(value)]);

  const dragState = React.useRef<{
    type: 'new' | 'move' | 'resize-start' | 'resize-end';
    blockId?: string;
    newBlockId?: string;
    anchorMin?: number;        // for 'new': click position
    dragOffsetMin?: number;    // for 'move': offset from block start to click
  } | null>(null);

  // ── Coordinate utils ──

  function xToMinutes(clientX: number): number {
    const rect = trackRef.current?.getBoundingClientRect();
    if (!rect) return 0;
    const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
    return snapToQuarter(ratio * 1440);
  }

  function minutesToPercent(min: number): number {
    return (min / 1440) * 100;
  }

  // ── Track click → create new block ──

  function handleTrackMouseDown(e: React.MouseEvent<HTMLDivElement>) {
    if (readOnly) return;
    // Only if clicking directly on the track (not a handle or block body)
    if ((e.target as HTMLElement) !== trackRef.current &&
        !(e.target as HTMLElement).classList.contains('hor-track-bg')) return;

    e.preventDefault();
    const anchorMin = xToMinutes(e.clientX);
    const id = Math.random().toString(36).slice(2);
    const newBlock: Block = { id, startMin: anchorMin, endMin: Math.min(1440, anchorMin + 60) };

    setBlocks(prev => {
      const next = [...prev, newBlock];
      onChange(periodsFromBlocks(next));
      return next;
    });

    dragState.current = { type: 'resize-end', blockId: id };
    window.addEventListener('mousemove', handleGlobalMouseMove);
    window.addEventListener('mouseup', handleGlobalMouseUp);
  }

  // ── Block body drag (move) ──

  function handleBlockMouseDown(e: React.MouseEvent, blockId: string) {
    if (readOnly) return;
    e.preventDefault();
    e.stopPropagation();
    const block = blocks.find(b => b.id === blockId);
    if (!block) return;
    const clickMin = xToMinutes(e.clientX);
    dragState.current = {
      type: 'move',
      blockId,
      dragOffsetMin: clickMin - block.startMin,
    };
    window.addEventListener('mousemove', handleGlobalMouseMove);
    window.addEventListener('mouseup', handleGlobalMouseUp);
  }

  // ── Handle drag (resize start / end) ──

  function handleResizeMouseDown(e: React.MouseEvent, blockId: string, which: 'start' | 'end') {
    if (readOnly) return;
    e.preventDefault();
    e.stopPropagation();
    dragState.current = { type: which === 'start' ? 'resize-start' : 'resize-end', blockId };
    window.addEventListener('mousemove', handleGlobalMouseMove);
    window.addEventListener('mouseup', handleGlobalMouseUp);
  }

  // ── Global mouse move ──

  const handleGlobalMouseMove = React.useCallback((e: MouseEvent) => {
    const ds = dragState.current;
    if (!ds || !ds.blockId) return;

    const curMin = xToMinutes(e.clientX);

    setBlocks(prev => prev.map(b => {
      if (b.id !== ds.blockId) return b;
      if (ds.type === 'resize-end') {
        const newEnd = Math.max(b.startMin + 15, Math.min(1440, curMin));
        return { ...b, endMin: newEnd };
      }
      if (ds.type === 'resize-start') {
        const newStart = Math.max(0, Math.min(b.endMin - 15, curMin));
        return { ...b, startMin: newStart };
      }
      if (ds.type === 'move') {
        const offset = ds.dragOffsetMin ?? 0;
        const duration = b.endMin - b.startMin;
        const newStart = Math.max(0, Math.min(1440 - duration, curMin - offset));
        return { ...b, startMin: newStart, endMin: newStart + duration };
      }
      return b;
    }));
  }, []);

  // ── Global mouse up ──

  const handleGlobalMouseUp = React.useCallback(() => {
    setBlocks(prev => {
      const resolved = resolveOverlaps(prev);
      onChange(periodsFromBlocks(resolved));
      return resolved;
    });
    dragState.current = null;
    window.removeEventListener('mousemove', handleGlobalMouseMove);
    window.removeEventListener('mouseup', handleGlobalMouseUp);
  }, [handleGlobalMouseMove, onChange]);

  // Cleanup on unmount
  React.useEffect(() => {
    return () => {
      window.removeEventListener('mousemove', handleGlobalMouseMove);
      window.removeEventListener('mouseup', handleGlobalMouseUp);
    };
  }, [handleGlobalMouseMove, handleGlobalMouseUp]);

  // ── Remove block ──

  function removeBlock(blockId: string) {
    setBlocks(prev => {
      const next = prev.filter(b => b.id !== blockId);
      onChange(periodsFromBlocks(next));
      return next;
    });
  }

  // ── Total work/rest hours for display ──
  // blocks ARE work periods (amber = work). Sum of block durations = total work.

  const totalWorkMin = blocks.reduce((sum, b) => sum + Math.max(0, b.endMin - b.startMin), 0);
  const totalWorkH = (totalWorkMin / 60).toFixed(1);
  const totalRestH = ((1440 - totalWorkMin) / 60).toFixed(1);

  return (
    <div style={{ width: '100%', userSelect: 'none' }}>
      {/* Hour labels — every 2 hours, absolutely positioned so they align with tick marks */}
      <div style={{ position: 'relative', height: 12, marginBottom: 2 }}>
        {Array.from({ length: 13 }, (_, i) => {
          const hour = i * 2;
          const pct = (hour / 24) * 100;
          return (
            <span
              key={hour}
              style={{
                position: 'absolute',
                left: `${pct}%`,
                transform: hour === 0 ? 'none' : hour === 24 ? 'translateX(-100%)' : 'translateX(-50%)',
                fontFamily: 'var(--font-mono)',
                fontSize: 8,
                color: 'var(--txt-ghost)',
                letterSpacing: '0.04em',
                lineHeight: '12px',
                pointerEvents: 'none',
              }}
            >
              {String(hour).padStart(2, '0')}
            </span>
          );
        })}
      </div>

      {/* Track */}
      <div
        ref={trackRef}
        className="hor-track-bg"
        onMouseDown={handleTrackMouseDown}
        style={{
          position: 'relative',
          height: 28,
          background: 'var(--surface-subtle)',
          borderRadius: 'var(--radius-pill)',
          border: '1px solid var(--border-chrome)',
          cursor: readOnly ? 'default' : 'crosshair',
          overflow: 'visible',
        }}
      >
        {/* Hour tick marks — every hour, with 6h anchors brighter */}
        {Array.from({ length: 25 }, (_, i) => (
          <div key={i} style={{
            position: 'absolute',
            left: `${(i / 24) * 100}%`,
            top: 0,
            bottom: 0,
            width: 1,
            background: i % 6 === 0 ? 'var(--border-top)' : i % 2 === 0 ? 'var(--border-sub)' : 'var(--border-faint)',
            pointerEvents: 'none',
          }} />
        ))}

        {/* Work blocks (amber = WORK) */}
        {blocks.map(block => {
          const left = minutesToPercent(block.startMin);
          const width = minutesToPercent(block.endMin - block.startMin);
          const durationMin = block.endMin - block.startMin;
          const label = `${toHHMM(block.startMin)}–${toHHMM(block.endMin)}`;

          return (
            <div
              key={block.id}
              style={{
                position: 'absolute',
                left: `${left}%`,
                width: `${width}%`,
                top: 1,
                bottom: 1,
                background: 'var(--amber-bg)',
                border: '1px solid var(--amber-border)',
                borderRadius: 3,
                display: 'flex',
                alignItems: 'center',
                minWidth: 4,
                zIndex: 2,
              }}
            >
              {/* Left handle */}
              {!readOnly && (
                <div
                  onMouseDown={e => handleResizeMouseDown(e, block.id, 'start')}
                  style={{
                    position: 'absolute',
                    left: -1,
                    top: 0,
                    bottom: 0,
                    width: 8,
                    cursor: 'ew-resize',
                    zIndex: 3,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <div style={{ width: 2, height: 10, background: 'var(--amber)', borderRadius: 1 }} />
                </div>
              )}

              {/* Block body (drag to move) + label */}
              <div
                onMouseDown={e => handleBlockMouseDown(e, block.id)}
                style={{
                  flex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: readOnly ? 'default' : 'grab',
                  overflow: 'hidden',
                  height: '100%',
                }}
              >
                {durationMin >= 90 && (
                  <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 8,
                    color: 'var(--amber)',
                    whiteSpace: 'nowrap',
                    pointerEvents: 'none',
                  }}>{label}</span>
                )}
              </div>

              {/* Right handle */}
              {!readOnly && (
                <div
                  onMouseDown={e => handleResizeMouseDown(e, block.id, 'end')}
                  style={{
                    position: 'absolute',
                    right: -1,
                    top: 0,
                    bottom: 0,
                    width: 8,
                    cursor: 'ew-resize',
                    zIndex: 3,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <div style={{ width: 2, height: 10, background: 'var(--amber)', borderRadius: 1 }} />
                </div>
              )}

              {/* Remove button (floats above, top-right) */}
              {!readOnly && (
                <button
                  onMouseDown={e => e.stopPropagation()}
                  onClick={() => removeBlock(block.id)}
                  style={{
                    position: 'absolute',
                    top: -8,
                    right: -8,
                    width: 14,
                    height: 14,
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--surface-el)',
                    border: '1px solid var(--border-top)',
                    color: 'var(--txt2)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 8,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 10,
                    lineHeight: 1,
                  }}
                >×</button>
              )}
            </div>
          );
        })}
      </div>

      {/* Summary */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-3)',
        marginTop: 5,
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        color: 'var(--txt-ghost)',
      }}>
        <span style={{ color: 'var(--amber)' }}>WORK {totalWorkH}h</span>
        <span>REST {totalRestH}h</span>
        {!readOnly && blocks.length === 0 && (
          <span style={{ color: 'var(--txt-ghost)', fontStyle: 'italic' }}>
            click track to add work period — blank = 24h rest
          </span>
        )}
      </div>
    </div>
  );
}
