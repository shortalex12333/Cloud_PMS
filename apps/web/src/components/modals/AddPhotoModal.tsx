/**
 * AddPhotoModal Component
 *
 * Generic modal for adding photos to any entity type
 * Supports: fault, work_order, equipment, checklist
 * Features: drag & drop, preview, caption
 */

'use client';

import { useState, useCallback, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useActionHandler } from '@/hooks/useActionHandler';
import {
  Camera,
  Loader2,
  AlertCircle,
  Wrench,
  Cog,
  ClipboardList,
  Upload,
  X,
  Image as ImageIcon,
  FileImage,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Validation schema
const addPhotoSchema = z.object({
  entity_type: z.enum(['fault', 'work_order', 'equipment', 'checklist']),
  entity_id: z.string().min(1, 'Entity ID is required'),
  caption: z.string().max(500, 'Caption too long').optional(),
});

type AddPhotoFormData = z.infer<typeof addPhotoSchema>;

type EntityType = 'fault' | 'work_order' | 'equipment' | 'checklist';

interface AddPhotoModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  context: {
    entity_type: EntityType;
    entity_id: string;
    entity_title: string;
    entity_subtitle?: string;
  };
  onSuccess?: () => void;
}

const ENTITY_CONFIG: Record<EntityType, { icon: React.ElementType; color: string; label: string }> = {
  fault: { icon: AlertCircle, color: 'text-red-500 bg-red-50 border-red-200', label: 'Fault' },
  work_order: { icon: Wrench, color: 'text-celeste-accent bg-celeste-accent-line border-celeste-accent-line', label: 'Work Order' },
  equipment: { icon: Cog, color: 'text-celeste-accent-500 bg-celeste-accent-50 border-celeste-accent-200', label: 'Equipment' },
  checklist: { icon: ClipboardList, color: 'text-restricted-green-500 bg-restricted-green-50 border-restricted-green-200', label: 'Checklist' },
};

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic'];

export function AddPhotoModal({
  open,
  onOpenChange,
  context,
  onSuccess,
}: AddPhotoModalProps) {
  const { executeAction, isLoading } = useActionHandler();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const config = ENTITY_CONFIG[context.entity_type];
  const EntityIcon = config.icon;

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<AddPhotoFormData>({
    resolver: zodResolver(addPhotoSchema) as any,
    defaultValues: {
      entity_type: context.entity_type,
      entity_id: context.entity_id,
      caption: '',
    },
  });

  const validateFile = (file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return 'File type not supported. Use JPEG, PNG, or WebP.';
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File too large. Maximum size is 10MB.';
    }
    return null;
  };

  const handleFileSelect = useCallback((file: File) => {
    const error = validateFile(file);
    if (error) {
      setUploadError(error);
      return;
    }

    setUploadError(null);
    setSelectedFile(file);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setPreview(null);
    setUploadError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const onSubmit = async (data: AddPhotoFormData) => {
    if (!selectedFile) {
      setUploadError('Please select a photo');
      return;
    }

    const actionName = `add_${context.entity_type}_photo` as const;

    // In production, this would upload to storage and get URL
    const response = await executeAction(
      actionName as any,
      {
        entity_type: data.entity_type,
        entity_id: data.entity_id,
        caption: data.caption,
        file_name: selectedFile.name,
        file_size: selectedFile.size,
        file_type: selectedFile.type,
        // In production: photo_url from upload
      },
      {
        successMessage: 'Photo added successfully',
        refreshData: true,
      }
    );

    if (response?.success) {
      handleClose();
      onSuccess?.();
    }
  };

  const handleClose = () => {
    reset();
    clearFile();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5 text-celeste-accent" />
            Add Photo
          </DialogTitle>
          <DialogDescription>
            Upload a photo for this {config.label.toLowerCase()}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit as any)} className="space-y-5">
          {/* Entity Context */}
          <div className={cn('p-3 rounded-lg border', config.color)}>
            <div className="flex items-center gap-3">
              <EntityIcon className="h-5 w-5" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-celeste-black truncate">{context.entity_title}</p>
                {context.entity_subtitle && (
                  <p className="typo-body text-celeste-text-secondary truncate">{context.entity_subtitle}</p>
                )}
              </div>
            </div>
          </div>

          {/* Drop Zone */}
          {!preview ? (
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                'border-2 border-dashed rounded-[10px] p-8',
                'flex flex-col items-center justify-center gap-3',
                'cursor-pointer transition-colors',
                isDragging
                  ? 'border-celeste-accent bg-celeste-accent-line'
                  : 'border-celeste-border hover:border-celeste-text-muted bg-celeste-bg-primary hover:bg-celeste-bg-secondary'
              )}
            >
              <div className={cn(
                'w-12 h-12 rounded-full flex items-center justify-center',
                isDragging ? 'bg-celeste-accent-subtle' : 'bg-celeste-border'
              )}>
                <Upload className={cn(
                  'h-6 w-6',
                  isDragging ? 'text-celeste-accent' : 'text-celeste-text-disabled'
                )} />
              </div>
              <div className="text-center">
                <p className="typo-body font-medium text-celeste-text-secondary">
                  {isDragging ? 'Drop photo here' : 'Click or drag photo to upload'}
                </p>
                <p className="typo-meta text-celeste-text-disabled mt-1">
                  JPEG, PNG, WebP up to 10MB
                </p>
              </div>
            </div>
          ) : (
            // Preview - using img for blob URL (Next Image doesn't support blob URLs)
            <div className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={preview}
                alt="Preview"
                className="w-full h-64 object-cover rounded-lg"
              />
              <button
                type="button"
                onClick={clearFile}
                className={cn(
                  'absolute top-2 right-2',
                  'w-8 h-8 rounded-full',
                  'bg-black/60 hover:bg-black/80',
                  'flex items-center justify-center',
                  'text-white transition-colors'
                )}
              >
                <X className="w-[18px] h-[18px]" />
              </button>
              <div className="absolute bottom-2 left-2 right-2">
                <div className="bg-black/60 rounded-lg px-3 py-1.5">
                  <div className="flex items-center gap-2 text-white typo-body">
                    <FileImage className="h-4 w-4" />
                    <span className="truncate flex-1">{selectedFile?.name}</span>
                    <span className="text-white/70 typo-meta">
                      {selectedFile && (selectedFile.size / 1024 / 1024).toFixed(1)}MB
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES.join(',')}
            onChange={handleInputChange}
            className="hidden"
          />

          {uploadError && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="typo-body text-red-700 flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                {uploadError}
              </p>
            </div>
          )}

          {/* Caption */}
          <div className="space-y-2">
            <Label htmlFor="caption">Caption (Optional)</Label>
            <Input
              id="caption"
              {...register('caption')}
              placeholder="Add a description for this photo..."
              className={errors.caption ? 'border-red-500' : ''}
            />
            {errors.caption && (
              <p className="typo-body text-red-600">{errors.caption.message}</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={isLoading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading || !selectedFile}>
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <Camera className="h-4 w-4 mr-2" />
                  Upload Photo
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
