/**
 * LinkEmailModal Component
 *
 * Allows users to manually link an email thread to an object.
 * Features:
 * - Search dropdown for WO, equipment, parts, faults, POs, suppliers
 * - Type filter tabs
 * - Real-time search with debounce
 */

'use client';

import { useState, useEffect, useMemo } from 'react';
import { Link2, Loader2, AlertCircle, Search, X, Wrench, Package, AlertTriangle, FileText, Users, CheckCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useObjectSearch, useCreateLink, useChangeLink, type SearchResult } from '@/hooks/useEmailData';
import { cn } from '@/lib/utils';

interface LinkEmailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  threadId: string;
  threadSubject?: string;
  existingLinkId?: string; // For change mode
  existingObjectType?: string;
  existingObjectId?: string;
}

const OBJECT_TYPES = [
  { value: 'work_order', label: 'Work Orders', icon: Wrench },
  { value: 'equipment', label: 'Equipment', icon: Package },
  { value: 'part', label: 'Parts', icon: Package },
  { value: 'fault', label: 'Faults', icon: AlertTriangle },
  { value: 'purchase_order', label: 'Purchase Orders', icon: FileText },
  { value: 'supplier', label: 'Suppliers', icon: Users },
];

export function LinkEmailModal({
  open,
  onOpenChange,
  threadId,
  threadSubject,
  existingLinkId,
  existingObjectType,
  existingObjectId,
}: LinkEmailModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<string[]>(['work_order', 'equipment', 'part']);
  const [selectedObject, setSelectedObject] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isChangeMode = !!existingLinkId;

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Search query
  const { data: searchResults, isLoading: isSearching } = useObjectSearch(
    debouncedQuery,
    selectedTypes
  );

  const createLinkMutation = useCreateLink();
  const changeLinkMutation = useChangeLink();

  const handleSubmit = async () => {
    if (!selectedObject) {
      setError('Please select an object to link to');
      return;
    }

    setError(null);

    try {
      if (isChangeMode && existingLinkId) {
        await changeLinkMutation.mutateAsync({
          linkId: existingLinkId,
          newObjectType: selectedObject.type,
          newObjectId: selectedObject.id,
        });
      } else {
        await createLinkMutation.mutateAsync({
          threadId,
          objectType: selectedObject.type,
          objectId: selectedObject.id,
        });
      }

      // Success - close modal
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to link thread');
    }
  };

  const handleClose = () => {
    setSearchQuery('');
    setDebouncedQuery('');
    setSelectedObject(null);
    setError(null);
    onOpenChange(false);
  };

  const toggleType = (type: string) => {
    setSelectedTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const isPending = createLinkMutation.isPending || changeLinkMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Link2 className="h-5 w-5" />
            {isChangeMode ? 'Change Email Link' : 'Link Email to Object'}
          </DialogTitle>
          <DialogDescription>
            {threadSubject ? (
              <span className="line-clamp-1">
                Linking: &quot;{threadSubject}&quot;
              </span>
            ) : (
              'Search and select an object to link this email thread to.'
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="py-4 space-y-4">
          {/* Type Filter Tabs */}
          <div className="flex flex-wrap gap-1">
            {OBJECT_TYPES.map(type => {
              const Icon = type.icon;
              const isSelected = selectedTypes.includes(type.value);
              return (
                <button
                  key={type.value}
                  onClick={() => toggleType(type.value)}
                  className={cn(
                    'inline-flex items-center gap-1 px-2 py-1 typo-meta rounded-md transition-colors',
                    !isSelected && 'bg-surface-hover text-txt-secondary hover:bg-surface-active'
                  )}
                  style={isSelected ? { background: 'var(--teal-bg)', color: 'var(--mark)' } : undefined}
                >
                  <Icon className="h-3 w-3" />
                  {type.label}
                </button>
              );
            })}
          </div>

          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-txt-tertiary" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name, number, serial..."
              className="w-full pl-9 pr-3 py-2 typo-meta border rounded-md placeholder:text-txt-tertiary focus:outline-none focus:ring-2"
              style={{ borderColor: 'var(--border-sub)', background: 'var(--surface-el)', color: 'var(--txt)', ['--tw-ring-color' as string]: 'var(--teal-bg)' }}
              autoFocus
            />
            {isSearching && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-txt-tertiary" />
            )}
          </div>

          {/* Search Results */}
          <div className="border border-border-sub rounded-md max-h-[240px] overflow-y-auto">
            {debouncedQuery.length < 2 ? (
              <div className="p-4 text-center typo-meta text-txt-secondary">
                Type at least 2 characters to search
              </div>
            ) : isSearching ? (
              <div className="p-4 text-center">
                <Loader2 className="h-5 w-5 animate-spin mx-auto text-txt-tertiary" />
              </div>
            ) : !searchResults?.results?.length ? (
              <div className="p-4 text-center typo-meta text-txt-secondary">
                No results found for &quot;{debouncedQuery}&quot;
              </div>
            ) : (
              <div className="divide-y divide-border-sub">
                {searchResults.results.map((result) => {
                  const isSelected = selectedObject?.id === result.id && selectedObject?.type === result.type;
                  const TypeIcon = OBJECT_TYPES.find(t => t.value === result.type)?.icon || Package;

                  return (
                    <button
                      key={`${result.type}-${result.id}`}
                      onClick={() => setSelectedObject(result)}
                      className={cn(
                        'w-full flex items-center gap-3 p-3 text-left transition-colors',
                        !isSelected && 'hover:bg-surface-hover'
                      )}
                      style={isSelected ? { background: 'var(--teal-bg)' } : undefined}
                    >
                      <TypeIcon
                        className={cn(
                          'h-4 w-4 flex-shrink-0',
                          !isSelected && 'text-txt-tertiary'
                        )}
                        style={isSelected ? { color: 'var(--mark)' } : undefined}
                      />
                      <div className="flex-1 min-w-0">
                        <p
                          className={cn(
                            'typo-meta truncate',
                            isSelected ? 'font-medium' : 'text-txt-primary'
                          )}
                          style={isSelected ? { color: 'var(--mark)' } : undefined}
                        >
                          {result.label}
                        </p>
                        <p className="typo-meta text-txt-secondary capitalize">
                          {result.type.replace('_', ' ')}
                          {result.status && ` • ${result.status}`}
                        </p>
                      </div>
                      {isSelected && (
                        <CheckCircle className="h-4 w-4 flex-shrink-0" style={{ color: 'var(--mark)' }} />
                      )}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Selected Object Display */}
          {selectedObject && (
            <div className="flex items-center gap-2 p-2 rounded-md" style={{ background: 'var(--teal-bg)' }}>
              <CheckCircle className="h-4 w-4" style={{ color: 'var(--mark)' }} />
              <span className="typo-meta flex-1 truncate" style={{ color: 'var(--mark)' }}>
                {selectedObject.label}
              </span>
              <button
                onClick={() => setSelectedObject(null)}
                className="p-1 rounded"
              >
                <X className="h-3 w-3" style={{ color: 'var(--mark)' }} />
              </button>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-md">
              <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="typo-meta text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isPending || !selectedObject}
          >
            {isPending && (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            )}
            {isChangeMode ? 'Change Link' : 'Link Email'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

