'use client';

/**
 * Global error boundary for the app shell.
 * Catches unhandled errors in route components and provides
 * a recovery UI instead of a white screen.
 */

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--surface-base)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-sans, -apple-system, BlinkMacSystemFont, system-ui, sans-serif)',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 12,
          textAlign: 'center',
          maxWidth: 380,
          padding: 24,
        }}
      >
        <h2 style={{ fontSize: 18, fontWeight: 500, color: 'var(--txt)' }}>
          Something went wrong
        </h2>
        <p style={{ fontSize: 13, color: 'var(--txt2)' }}>
          {error.message || 'An unexpected error occurred.'}
        </p>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button
            onClick={reset}
            style={{
              padding: '8px 20px',
              borderRadius: 6,
              background: 'var(--teal-bg)',
              border: '1px solid var(--mark-hover)',
              color: 'var(--mark)',
              fontSize: 12,
              fontWeight: 500,
              cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
            }}
          >
            Try again
          </button>
          <button
            onClick={() => (window.location.href = '/')}
            style={{
              padding: '8px 20px',
              borderRadius: 6,
              border: '1px solid var(--border-sub)',
              background: 'var(--surface-base)',
              color: 'var(--txt2)',
              fontSize: 12,
              cursor: 'pointer',
              fontFamily: 'var(--font-sans)',
            }}
          >
            Go home
          </button>
        </div>
      </div>
    </div>
  );
}
