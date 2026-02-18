/**
 * LoginPage
 * Apple-style minimal login
 */

import { Suspense } from 'react';
import LoginContent from './LoginContent';

export const dynamic = 'force-dynamic';

function LoginLoading() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="w-6 h-6 border-2 border-surface-border border-t-txt-secondary rounded-full animate-spin" />
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginLoading />}>
      <LoginContent />
    </Suspense>
  );
}
