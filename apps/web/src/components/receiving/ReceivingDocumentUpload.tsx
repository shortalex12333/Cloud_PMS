/**
 * Receiving Document Upload Component
 *
 * Camera capture + file upload for receiving documents (invoices, packing slips, photos)
 * Workflow: Capture → Upload → Extract → Review → Save
 */

'use client';

import { useState, useRef, useCallback } from 'react';
import { Camera, Upload, FileText, CheckCircle, XCircle, AlertCircle, Loader2, RefreshCw, Save } from 'lucide-react';
import { receivingApi, CelesteApiError } from '@/lib/apiClient';
import { saveExtractedData, autoPopulateLineItems, updateReceivingHeader } from '@/lib/receiving/saveExtractedData';
import { supabase } from '@/lib/supabaseClient';
import { cn } from '@/lib/utils';

interface ReceivingDocumentUploadProps {
  receivingId: string;
  onComplete?: (documentId: string, extractedData: any) => void;
  defaultDocType?: 'invoice' | 'packing_slip' | 'photo' | 'other';
}

type UploadStatus = 'idle' | 'uploading' | 'processing' | 'success' | 'error' | 'retrying';

export function ReceivingDocumentUpload({
  receivingId,
  onComplete,
  defaultDocType = 'other',
}: ReceivingDocumentUploadProps) {
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [docType, setDocType] = useState<'invoice' | 'packing_slip' | 'photo' | 'other'>(defaultDocType);
  const [comment, setComment] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [extractedData, setExtractedData] = useState<any>(null);
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);

  // Start camera
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' }, // Use back camera on mobile
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraActive(true);
      }
    } catch (err) {
      console.error('Failed to start camera:', err);
      setError('Camera access denied or unavailable');
    }
  }, []);

  // Stop camera
  const stopCamera = useCallback(() => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
      setIsCameraActive(false);
    }
  }, []);

  // Capture photo from camera
  const capturePhoto = useCallback(() => {
    if (!videoRef.current || !canvasRef.current) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], `receiving-${Date.now()}.jpg`, { type: 'image/jpeg' });
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(blob));
      stopCamera();
    }, 'image/jpeg', 0.9);
  }, [stopCamera]);

  // Handle file selection
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const validTypes = ['image/jpeg', 'image/png', 'image/heic', 'application/pdf'];
    if (!validTypes.includes(file.type)) {
      setError('Invalid file type. Please upload JPG, PNG, HEIC, or PDF.');
      return;
    }

    // Validate file size (15MB)
    const maxSize = 15 * 1024 * 1024;
    if (file.size > maxSize) {
      setError('File too large. Maximum size is 15MB.');
      return;
    }

    setSelectedFile(file);
    setError(null);

    // Create preview for images
    if (file.type.startsWith('image/')) {
      setPreviewUrl(URL.createObjectURL(file));
    } else {
      setPreviewUrl(null);
    }
  };

  // Upload with retry logic for 503
  const uploadWithRetry = async (file: File, attempt: number = 1): Promise<any> => {
    const maxAttempts = 3;
    const retryDelay = 30000; // 30 seconds for Render spin-up

    try {
      setStatus(attempt > 1 ? 'retrying' : 'uploading');
      setRetryCount(attempt);

      const result = await receivingApi.uploadDocument(receivingId, file, docType, comment);
      return result;
    } catch (err) {
      if (err instanceof CelesteApiError && err.status === 503 && attempt < maxAttempts) {
        // 503 Service Unavailable - Render service spinning up
        console.log(`[Upload] Attempt ${attempt} failed with 503, retrying in ${retryDelay / 1000}s...`);
        await new Promise((resolve) => setTimeout(resolve, retryDelay));
        return uploadWithRetry(file, attempt + 1);
      }
      throw err;
    }
  };

  // Handle upload
  const handleUpload = async () => {
    if (!selectedFile) return;

    setStatus('uploading');
    setError(null);
    setRetryCount(0);

    try {
      const result = await uploadWithRetry(selectedFile);

      setStatus('success');
      setDocumentId(result.document_id);
      setExtractedData(result.extracted_data || {});

      if (onComplete) {
        onComplete(result.document_id, result.extracted_data);
      }
    } catch (err) {
      setStatus('error');
      if (err instanceof CelesteApiError) {
        setError(err.message);
      } else {
        setError('Upload failed. Please try again.');
      }
    }
  };

  // Handle save to database
  const handleSave = async () => {
    if (!documentId) return;

    setIsSaving(true);
    setError(null);

    try {
      // Get yacht_id from current user
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      const yachtId = user.user_metadata?.yacht_id;
      if (!yachtId) {
        throw new Error('Yacht ID not found');
      }

      // Save document link and extraction results
      const saveResult = await saveExtractedData(
        receivingId,
        yachtId,
        documentId,
        docType,
        comment,
        extractedData
      );

      if (!saveResult.success) {
        throw new Error(saveResult.error || 'Failed to save data');
      }

      // Optionally auto-populate line items if extracted
      if (extractedData?.line_items && Array.isArray(extractedData.line_items)) {
        await autoPopulateLineItems(receivingId, yachtId, extractedData.line_items);
      }

      // Optionally update header fields if empty
      if (extractedData?.vendor_name || extractedData?.vendor_reference || extractedData?.total) {
        await updateReceivingHeader(receivingId, {
          vendor_name: extractedData.vendor_name,
          vendor_reference: extractedData.vendor_reference,
          total: extractedData.total,
          currency: extractedData.currency,
        });
      }

      setSaveSuccess(true);
      setIsSaving(false);
    } catch (err) {
      setIsSaving(false);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to save data to database');
      }
    }
  };

  // Reset form
  const reset = () => {
    setStatus('idle');
    setSelectedFile(null);
    setPreviewUrl(null);
    setExtractedData(null);
    setDocumentId(null);
    setError(null);
    setRetryCount(0);
    setIsSaving(false);
    setSaveSuccess(false);
    stopCamera();
  };

  return (
    <div className="bg-card border border-border rounded-lg p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <FileText className="h-6 w-6 text-primary" />
        <h3 className="text-lg font-semibold text-foreground">Upload Document</h3>
      </div>

      {/* Document Type Selector */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">Document Type</label>
        <select
          value={docType}
          onChange={(e) => setDocType(e.target.value as any)}
          disabled={status !== 'idle'}
          className="w-full px-3 py-2 bg-background border border-input rounded-md text-foreground"
        >
          <option value="invoice">Invoice</option>
          <option value="packing_slip">Packing Slip</option>
          <option value="photo">Photo</option>
          <option value="other">Other</option>
        </select>
      </div>

      {/* Comment (Optional) */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-foreground">Comment (Optional)</label>
        <input
          type="text"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          disabled={status !== 'idle'}
          placeholder="Add notes about this document..."
          className="w-full px-3 py-2 bg-background border border-input rounded-md text-foreground"
        />
      </div>

      {/* Camera or File Upload */}
      {!selectedFile && !isCameraActive && (
        <div className="flex gap-3">
          <button
            onClick={startCamera}
            disabled={status !== 'idle'}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <Camera className="h-5 w-5" />
            Take Photo
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={status !== 'idle'}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 transition-colors disabled:opacity-50"
          >
            <Upload className="h-5 w-5" />
            Upload File
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/heic,application/pdf"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>
      )}

      {/* Camera View */}
      {isCameraActive && (
        <div className="space-y-3">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            className="w-full rounded-md bg-black"
          />
          <canvas ref={canvasRef} className="hidden" />
          <div className="flex gap-3">
            <button
              onClick={capturePhoto}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              <Camera className="h-5 w-5" />
              Capture
            </button>
            <button
              onClick={stopCamera}
              className="px-4 py-3 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Preview */}
      {selectedFile && !extractedData && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{selectedFile.name}</span>
            <button
              onClick={reset}
              disabled={status === 'uploading' || status === 'retrying'}
              className="text-sm text-destructive hover:underline"
            >
              Remove
            </button>
          </div>

          {previewUrl && (
            <img src={previewUrl} alt="Preview" className="w-full rounded-md border border-border" />
          )}

          {/* Upload Button */}
          <button
            onClick={handleUpload}
            disabled={status === 'uploading' || status === 'retrying'}
            className={cn(
              'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-md transition-colors',
              status === 'uploading' || status === 'retrying'
                ? 'bg-secondary text-secondary-foreground'
                : 'bg-primary text-primary-foreground hover:bg-primary/90'
            )}
          >
            {(status === 'uploading' || status === 'retrying') && <Loader2 className="h-5 w-5 animate-spin" />}
            {status === 'retrying' && `Retrying (${retryCount}/3)...`}
            {status === 'uploading' && 'Uploading...'}
            {status === 'idle' && 'Upload & Process'}
          </button>
        </div>
      )}

      {/* Status Messages */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-md text-destructive">
          <XCircle className="h-5 w-5" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {status === 'retrying' && (
        <div className="flex items-center gap-2 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-md text-yellow-700 dark:text-yellow-400">
          <RefreshCw className="h-5 w-5 animate-spin" />
          <span className="text-sm">Service starting up, retrying in 30s...</span>
        </div>
      )}

      {status === 'success' && !extractedData && (
        <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-md text-green-700 dark:text-green-400">
          <CheckCircle className="h-5 w-5" />
          <span className="text-sm">Upload successful</span>
        </div>
      )}

      {/* Extracted Data Display */}
      {extractedData && (
        <div className="space-y-4 border-t border-border pt-4">
          <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
            <CheckCircle className="h-5 w-5" />
            <h4 className="font-semibold">Extraction Complete</h4>
          </div>

          {/* Display extracted data in table format */}
          <div className="bg-background border border-border rounded-md overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="px-4 py-2 text-left font-medium">Field</th>
                  <th className="px-4 py-2 text-left font-medium">Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(extractedData).map(([key, value]) => (
                  <tr key={key} className="border-t border-border">
                    <td className="px-4 py-2 font-medium text-muted-foreground">
                      {key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                    </td>
                    <td className="px-4 py-2 text-foreground">
                      {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Save Success Message */}
          {saveSuccess && (
            <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-md text-green-700 dark:text-green-400">
              <CheckCircle className="h-5 w-5" />
              <span className="text-sm">Data saved successfully</span>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={reset}
              disabled={isSaving}
              className="flex-1 px-4 py-2 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 transition-colors disabled:opacity-50"
            >
              Upload Another
            </button>
            {!saveSuccess && (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className={cn(
                  'flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md transition-colors',
                  isSaving
                    ? 'bg-secondary text-secondary-foreground'
                    : 'bg-primary text-primary-foreground hover:bg-primary/90'
                )}
              >
                {isSaving && <Loader2 className="h-4 w-4 animate-spin" />}
                {!isSaving && <Save className="h-4 w-4" />}
                {isSaving ? 'Saving...' : 'Save to Database'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
