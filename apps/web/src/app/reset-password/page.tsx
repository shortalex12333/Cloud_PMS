import { Suspense } from 'react';
import ResetPasswordClient from './ResetPasswordClient';

export const dynamic = 'force-dynamic';

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--surface-base)' }}>
          <div style={{ width: '32px', height: '32px', borderRadius: '50%', border: '3px solid var(--teal)', borderTopColor: 'transparent', animation: 'spin 0.8s linear infinite' }} />
        </div>
      }
    >
      <ResetPasswordClient />
    </Suspense>
  );
}
