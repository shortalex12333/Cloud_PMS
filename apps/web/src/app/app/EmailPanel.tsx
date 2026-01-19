'use client';

/**
 * EmailPanel - Slides from left
 *
 * Shows inbox/sent view when email-present state is active.
 * No URL change - purely state-driven.
 */

import { useSurface } from '@/contexts/SurfaceContext';
import { X, Inbox, Send, ChevronLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import { EmailInboxView } from '@/components/email/EmailInboxView';

export default function EmailPanel() {
  const { emailPanel, hideEmail, showEmail } = useSurface();
  const { visible, folder = 'inbox' } = emailPanel;

  return (
    <div
      data-testid="email-panel"
      data-visible={visible}
      className={cn(
        'absolute inset-y-0 left-0 w-96 bg-gray-900/95 border-r border-gray-700/50',
        'transform transition-transform duration-300 ease-out z-20',
        'backdrop-blur-sm shadow-2xl',
        visible ? 'translate-x-0' : '-translate-x-full'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700/50">
        <div className="flex items-center gap-4">
          <button
            onClick={hideEmail}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            aria-label="Close email panel"
          >
            <ChevronLeft className="w-5 h-5 text-gray-400" />
          </button>
          <h2 className="text-lg font-semibold text-white">Email</h2>
        </div>
        <button
          onClick={hideEmail}
          className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          aria-label="Close panel"
        >
          <X className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      {/* Folder tabs */}
      <div className="flex border-b border-gray-700/50">
        <button
          onClick={() => showEmail({ folder: 'inbox' })}
          className={cn(
            'flex-1 py-3 px-4 flex items-center justify-center gap-2 text-sm font-medium',
            'transition-colors border-b-2',
            folder === 'inbox'
              ? 'border-blue-500 text-blue-400 bg-blue-500/10'
              : 'border-transparent text-gray-400 hover:text-gray-300 hover:bg-gray-800/50'
          )}
        >
          <Inbox className="w-4 h-4" />
          Inbox
        </button>
        <button
          onClick={() => showEmail({ folder: 'sent' })}
          className={cn(
            'flex-1 py-3 px-4 flex items-center justify-center gap-2 text-sm font-medium',
            'transition-colors border-b-2',
            folder === 'sent'
              ? 'border-blue-500 text-blue-400 bg-blue-500/10'
              : 'border-transparent text-gray-400 hover:text-gray-300 hover:bg-gray-800/50'
          )}
        >
          <Send className="w-4 h-4" />
          Sent
        </button>
      </div>

      {/* Email content */}
      <div className="flex-1 overflow-y-auto">
        {folder === 'inbox' ? (
          <EmailInboxView className="p-4" />
        ) : (
          <div className="text-center py-12 px-4">
            <Send className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-sm">Sent emails</p>
            <p className="text-gray-500 text-xs mt-2">
              Sent folder is not yet implemented
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
