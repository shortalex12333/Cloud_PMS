'use client';

/**
 * TimeSlider — 24-hour rest period input
 *
 * Interaction:
 * - Click empty track → creates a new 1-hour block at that position
 * - Drag left handle → resize block start
 * - Drag right handle → resize block end
 * - Drag block body → move entire block
 * - "×" button on block → remove block
 *
 * Output (via onChange):
 *   rest_periods: [{start: "HH:MM", end: "HH:MM"}, ...]
 *   Sorted by start time, no overlaps enforced (backend validates).
 */

import * as React from 'react';

// ── Types ───────────────────────────────────────────────────────────────────

export interface RestPeriod {
  start: string; // "HH:MM"
  end: string;   // "HH:MM"
}

interface Block {
  id: string;
  startMin: number; // 0–1440
  endMin: number;   // 0–1440
}

interface TimeSliderProps {
  /** Initial rest periods from saved/submitted data */
  value?: RestPeriod[];
  /** Called every time blocks change */
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

const HOUR_LABELS = ['00', '03', '06', '09', '12', '15', '18', '21', '24'];

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
      onChange(periodsFromBlocks(prev));
      return prev;
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

  // ── Total rest hours for display ──

  const totalRestMin = blocks.reduce((sum, b) => sum + Math.max(0, b.endMin - b.startMin), 0);
  const totalRestH = (totalRestMin / 60).toFixed(1);
  const totalWorkH = ((1440 - totalRestMin) / 60).toFixed(1);

  return (
    <div style={{ width: '100%', userSelect: 'none' }}>
      {/* Hour labels */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, paddingLeft: 0 }}>
        {HOUR_LABELS.map(h => (
          <span key={h} style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 8,
            color: 'rgba(255,255,255,0.25)',
            letterSpacing: '0.04em',
            minWidth: 0,
          }}>{h}</span>
        ))}
      </div>

      {/* Track */}
      <div
        ref={trackRef}
        className="hor-track-bg"
        onMouseDown={handleTrackMouseDown}
        style={{
          position: 'relative',
          height: 28,
          background: 'rgba(255,255,255,0.05)',
          borderRadius: 4,
          border: '1px solid rgba(255,255,255,0.08)',
          cursor: readOnly ? 'default' : 'crosshair',
          overflow: 'visible',
        }}
      >
        {/* Hour tick marks */}
        {Array.from({ length: 25 }, (_, i) => (
          <div key={i} style={{
            position: 'absolute',
            left: `${(i / 24) * 100}%`,
            top: 0,
            bottom: 0,
            width: 1,
            background: i % 6 === 0 ? 'rgba(255,255,255,0.10)' : 'rgba(255,255,255,0.04)',
            pointerEvents: 'none',
          }} />
        ))}

        {/* Rest blocks (teal = REST) */}
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
                background: 'rgba(90,171,204,0.35)',
                border: '1px solid rgba(90,171,204,0.55)',
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
                  <div style={{ width: 2, height: 10, background: 'rgba(90,171,204,0.8)', borderRadius: 1 }} />
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
                    color: 'rgba(90,171,204,0.9)',
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
                  <div style={{ width: 2, height: 10, background: 'rgba(90,171,204,0.8)', borderRadius: 1 }} />
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
                    borderRadius: '50%',
                    background: 'var(--surface-el, #1e1b18)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    color: 'rgba(255,255,255,0.6)',
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
        gap: 12,
        marginTop: 5,
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        color: 'rgba(255,255,255,0.35)',
      }}>
        <span style={{ color: 'rgba(90,171,204,0.7)' }}>REST {totalRestH}h</span>
        <span>WORK {totalWorkH}h</span>
        {!readOnly && blocks.length === 0 && (
          <span style={{ color: 'rgba(255,255,255,0.22)', fontStyle: 'italic' }}>
            click track to add rest period
          </span>
        )}
      </div>
    </div>
  );
}
