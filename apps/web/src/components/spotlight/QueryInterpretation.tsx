'use client';

/**
 * QueryInterpretation — "Understood" panel
 * Per elegant.html prototype: teal left-border, italic label, mono terms.
 */

import React from 'react';

interface QueryInterpretationProps {
  query: string;
}

const NOISE = new Set([
  'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or',
  'is', 'are', 'was', 'were', 'be', 'been', 'has', 'have', 'had',
  'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
  'with', 'from', 'by', 'about', 'that', 'this', 'it', 'my', 'me',
  'what', 'where', 'when', 'how', 'which', 'who', 'all', 'any',
  'find', 'show', 'get', 'list', 'search',
]);

function extractTerms(query: string): string[] {
  return query.toLowerCase().split(/\s+/).filter(w => w.length > 1 && !NOISE.has(w));
}

export default function QueryInterpretation({ query }: QueryInterpretationProps) {
  const terms = extractTerms(query);
  if (terms.length === 0) return null;

  return (
    <div style={{ marginTop: 6, marginBottom: 2 }}>
      <div style={{
        display: 'flex', alignItems: 'baseline', flexWrap: 'wrap', gap: 2,
        padding: '5px 10px', borderLeft: '2px solid #3A7C9D', opacity: 0.88,
      }}>
        <span style={{ fontSize: 10, fontStyle: 'italic', color: 'rgba(255,255,255,0.70)', marginRight: 6, flexShrink: 0 }}>
          Understood
        </span>
        {terms.map((term, i) => (
          <React.Fragment key={i}>
            {i > 0 && <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.40)', userSelect: 'none', padding: '0 2px' }}>·</span>}
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 500, color: '#5AABCC' }}>{term}</span>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
