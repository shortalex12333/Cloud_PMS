/**
 * Home Page
 */

'use client';

import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';

export default function Home() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Welcome to CelesteOS
        </h1>
        <p className="text-lg text-gray-600 mb-8">
          Intelligent Yacht Management System
        </p>

        {user ? (
          <div className="space-y-4">
            <p className="text-gray-700">Logged in as: {user.email}</p>
            <Link
              href="/settings"
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Go to Settings
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-gray-700">Please log in to continue</p>
            <button
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              onClick={() => {
                // TODO: Implement login flow
                alert('Login flow not yet implemented. Please configure Supabase auth.');
              }}
            >
              Log In
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
