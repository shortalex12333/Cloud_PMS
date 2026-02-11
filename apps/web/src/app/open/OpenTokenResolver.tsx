'use client';

/**
 * OpenTokenResolver - Client Component for Token Resolution
 *
 * Handles the actual token resolution flow:
 * 1. Read token from URL
 * 2. Check authentication
 * 3. Resolve token via handover-export API
 * 4. Navigate to entity
 * 5. Clean up URL
 */

import { useEffect, useState, useRef } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import {
  resolveOpenToken,
  ResolveError,
  type ResolveResponse,
} from '@/lib/handoverExportClient';
import { AuthError } from '@/lib/authHelpers';
import { Loader2, AlertCircle, XCircle, ShieldX, Clock, HelpCircle } from 'lucide-react';

type ResolverState =
  | 'loading'
  | 'authenticating'
  | 'resolving'
  | 'success'
  | 'error_expired'
  | 'error_invalid'
  | 'error_yacht'
  | 'error_not_found'
  | 'error_unsupported'
  | 'error_auth'
  | 'error_unknown'
  | 'no_token';

interface ErrorDisplay {
  icon: React.ReactNode;
  title: string;
  message: string;
  action?: string;
}

const ERROR_DISPLAYS: Record<string, ErrorDisplay> = {
  error_expired: {
    icon: <Clock className="w-8 h-8 text-orange-500" />,
    title: 'Link Expired',
    message: 'This link has expired. Please request a new handover export.',
    action: 'Return to App',
  },
  error_invalid: {
    icon: <XCircle className="w-8 h-8 text-red-500" />,
    title: 'Invalid Link',
    message: 'This link is invalid or has been tampered with.',
    action: 'Return to App',
  },
  error_yacht: {
    icon: <ShieldX className="w-8 h-8 text-red-500" />,
    title: 'Access Denied',
    message: 'You do not have access to this resource. It belongs to a different yacht.',
    action: 'Return to App',
  },
  error_not_found: {
    icon: <HelpCircle className="w-8 h-8 text-yellow-500" />,
    title: 'Not Found',
    message: 'The linked item could not be found. It may have been deleted.',
    action: 'Return to App',
  },
  error_unsupported: {
    icon: <AlertCircle className="w-8 h-8 text-yellow-500" />,
    title: 'Link Type Not Supported',
    message: 'This type of link is not yet supported. Please view the item manually.',
    action: 'Return to App',
  },
  error_auth: {
    icon: <ShieldX className="w-8 h-8 text-red-500" />,
    title: 'Authentication Required',
    message: 'Please sign in to access this link.',
    action: 'Sign In',
  },
  error_unknown: {
    icon: <AlertCircle className="w-8 h-8 text-red-500" />,
    title: 'Something Went Wrong',
    message: 'We encountered an error processing this link. Please try again.',
    action: 'Return to App',
  },
  no_token: {
    icon: <HelpCircle className="w-8 h-8 text-celeste-text-disabled" />,
    title: 'No Link Token',
    message: 'No token was provided in the URL.',
    action: 'Return to App',
  },
};

export default function OpenTokenResolver() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, loading: authLoading, session } = useAuth();
  const [state, setState] = useState<ResolverState>('loading');
  const [resolveData, setResolveData] = useState<ResolveResponse | null>(null);
  const processedRef = useRef(false);

  const token = searchParams.get('t');

  useEffect(() => {
    // Don't process if already processed
    if (processedRef.current) return;

    // Wait for auth to finish loading
    if (authLoading) {
      setState('authenticating');
      return;
    }

    // No token provided
    if (!token) {
      setState('no_token');
      processedRef.current = true;
      return;
    }

    // Not authenticated - redirect to login
    if (!user || !session) {
      setState('error_auth');
      // Store return URL and redirect to login
      const returnUrl = `/open?t=${encodeURIComponent(token)}`;
      sessionStorage.setItem('celeste_return_url', returnUrl);
      // Don't auto-redirect, let user click sign in
      processedRef.current = true;
      return;
    }

    // Ready to resolve
    processedRef.current = true;
    setState('resolving');

    const resolve = async () => {
      try {
        console.log('[OpenTokenResolver] Resolving token...');
        const data = await resolveOpenToken(token);
        setResolveData(data);
        setState('success');

        console.log('[OpenTokenResolver] Token resolved:', {
          type: data.focus.type,
          id: data.focus.id.substring(0, 8) + '...',
        });

        // Navigate to /app with entity focus via query params
        // DeepLinkHandler will pick this up
        const params = new URLSearchParams({
          entity: data.focus.type,
          id: data.focus.id,
        });

        // Small delay to show success state, then navigate
        setTimeout(() => {
          // Replace URL to remove token from history (security)
          router.replace(`/app?${params.toString()}`);
        }, 300);
      } catch (error) {
        console.error('[OpenTokenResolver] Resolution failed:', error);

        if (error instanceof ResolveError) {
          switch (error.code) {
            case 'TOKEN_EXPIRED':
              setState('error_expired');
              break;
            case 'TOKEN_INVALID':
              setState('error_invalid');
              break;
            case 'YACHT_MISMATCH':
              setState('error_yacht');
              break;
            case 'ENTITY_NOT_FOUND':
              setState('error_not_found');
              break;
            case 'UNSUPPORTED_TYPE':
            case 'UNKNOWN_TYPE':
              setState('error_unsupported');
              break;
            case 'AUTH_REQUIRED':
              setState('error_auth');
              break;
            default:
              setState('error_unknown');
          }
        } else if (error instanceof AuthError) {
          setState('error_auth');
        } else {
          setState('error_unknown');
        }
      }
    };

    resolve();
  }, [token, user, session, authLoading, router]);

  // Handle action button click
  const handleAction = () => {
    if (state === 'error_auth') {
      // Redirect to login with return URL
      const returnUrl = token ? `/open?t=${encodeURIComponent(token)}` : '/app';
      sessionStorage.setItem('celeste_return_url', returnUrl);
      router.push('/login');
    } else {
      // Return to app
      router.replace('/app');
    }
  };

  // Loading/authenticating state
  if (state === 'loading' || state === 'authenticating') {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-celeste-accent animate-spin" />
          <p className="text-sm text-[#98989f]">
            {state === 'authenticating' ? 'Checking authentication...' : 'Loading...'}
          </p>
        </div>
      </div>
    );
  }

  // Resolving state
  if (state === 'resolving') {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="w-8 h-8 text-celeste-accent animate-spin" />
          <p className="text-sm text-[#98989f]">Opening link...</p>
        </div>
      </div>
    );
  }

  // Success state (brief, then redirects)
  if (state === 'success' && resolveData) {
    return (
      <div className="min-h-screen bg-[#000000] flex items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
            <svg
              className="w-5 h-5 text-green-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <p className="text-sm text-[#98989f]">
            Opening {resolveData.focus.type.replace('_', ' ')}...
          </p>
        </div>
      </div>
    );
  }

  // Error states
  const errorDisplay = ERROR_DISPLAYS[state] || ERROR_DISPLAYS.error_unknown;

  return (
    <div className="min-h-screen bg-[#000000] flex items-center justify-center p-6">
      <div
        className="w-full max-w-sm text-center"
        data-testid="open-token-error"
        data-error-state={state}
      >
        {/* Icon */}
        <div className="flex justify-center mb-6">{errorDisplay.icon}</div>

        {/* Title */}
        <h1 className="text-xl font-semibold text-white mb-2">{errorDisplay.title}</h1>

        {/* Message */}
        <p className="text-sm text-[#98989f] mb-8">{errorDisplay.message}</p>

        {/* Action button */}
        {errorDisplay.action && (
          <button
            onClick={handleAction}
            className="px-6 py-2.5 rounded-lg bg-celeste-accent hover:bg-celeste-accent-hover text-white text-sm font-medium transition-colors"
          >
            {errorDisplay.action}
          </button>
        )}
      </div>
    </div>
  );
}
