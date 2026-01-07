/**
 * LoginPage
 * Apple-style minimal login
 */

import { Suspense } from 'react';
import LoginContent from './LoginContent';

export const dynamic = 'force-dynamic';

function LoginLoading() {
  return (
    <div className="min-h-screen bg-[#000000] flex items-center justify-center">
      <div className="w-6 h-6 border-2 border-[#3d3d3f] border-t-[#86868b] rounded-full animate-spin" />
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
