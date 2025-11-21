/**
 * LocationFilter Component
 *
 * Generic hierarchical location filter
 * Entity-agnostic - receives location options from parent
 */

'use client';

import { useState } from 'react';
import { MapPin } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';

export interface LocationFilterValue {
  deck?: string;
  room?: string;
  storage?: string;
}

interface LocationFilterProps {
  options: {
    decks: string[];
    rooms: string[];
    storages: string[];
  };
  value: LocationFilterValue;
  onApply: (location: LocationFilterValue) => void;
  onClear: () => void;
}

export function LocationFilter({
  options,
  value,
  onApply,
  onClear,
}: LocationFilterProps) {
  const [localValue, setLocalValue] = useState<LocationFilterValue>(value || {});

  const handleApply = () => {
    // Only apply if at least one field is selected
    if (localValue.deck || localValue.room || localValue.storage) {
      onApply(localValue);
    }
  };

  const handleClear = () => {
    setLocalValue({});
    onClear();
  };

  const hasValue = value?.deck || value?.room || value?.storage;

  return (
    <div className="flex items-end gap-2">
      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">
          <MapPin className="h-3 w-3 inline mr-1" />
          Location
        </Label>

        <div className="flex gap-2">
          {/* Deck Selector */}
          <Select
            value={localValue.deck || ''}
            onValueChange={(val) =>
              setLocalValue((prev) => ({ ...prev, deck: val || undefined }))
            }
          >
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="Deck" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Any Deck</SelectItem>
              {options.decks.map((deck) => (
                <SelectItem key={deck} value={deck}>
                  {deck}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Room Selector */}
          <Select
            value={localValue.room || ''}
            onValueChange={(val) =>
              setLocalValue((prev) => ({ ...prev, room: val || undefined }))
            }
          >
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Room" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Any Room</SelectItem>
              {options.rooms.map((room) => (
                <SelectItem key={room} value={room}>
                  {room}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Storage Selector */}
          <Select
            value={localValue.storage || ''}
            onValueChange={(val) =>
              setLocalValue((prev) => ({ ...prev, storage: val || undefined }))
            }
          >
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="Storage" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Any Storage</SelectItem>
              {options.storages.map((storage) => (
                <SelectItem key={storage} value={storage}>
                  {storage}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-1">
        <Button
          size="sm"
          onClick={handleApply}
          disabled={!localValue.deck && !localValue.room && !localValue.storage}
        >
          Apply
        </Button>
        {hasValue && (
          <Button size="sm" variant="ghost" onClick={handleClear}>
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}
