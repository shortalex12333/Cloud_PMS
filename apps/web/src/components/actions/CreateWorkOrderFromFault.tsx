/**
 * Create Work Order from Fault
 * ============================
 *
 * P0 Action #2: create_work_order_from_fault
 *
 * Flow:
 * 1. Fetch prefill data from API
 * 2. Show form (pre-filled, editable)
 * 3. User clicks "Next" → Preview
 * 4. User reviews changes and side effects
 * 5. User signs → Execute
 * 6. Success → Navigate to work order detail
 *
 * Based on spec: /action_specifications/cluster_02_DO_MAINTENANCE/create_work_order_from_fault.md
 */

import React, { useState, useEffect } from 'react';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';
import { useRouter } from 'next/navigation';

// Types
interface PrefillData {
  title: string;
  equipment_id: string | null;
  equipment_name: string;
  location: string;
  description: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  fault_id: string;
  fault_code: string;
}

interface DuplicateCheck {
  has_duplicate: boolean;
  existing_wo: {
    id: string;
    number: string;
    status: string;
    assigned_to: string | null;
    created_at: string;
    days_ago: number;
  } | null;
}

interface PreviewData {
  action: string;
  summary: string;
  entity_type: string;
  changes: Record<string, string>;
  side_effects: string[];
  requires_signature: boolean;
  warning: string | null;
}

type Step = 'loading' | 'form' | 'duplicate_warning' | 'preview' | 'signing' | 'success' | 'error';

interface Props {
  faultId: string;
  onCancel: () => void;
  onSuccess: (workOrderId: string) => void;
}

export default function CreateWorkOrderFromFault({ faultId, onCancel, onSuccess }: Props) {
  const router = useRouter();
  const supabase = createClientComponentClient();

  // State
  const [step, setStep] = useState<Step>('loading');
  const [prefillData, setPrefillData] = useState<PrefillData | null>(null);
  const [duplicateCheck, setDuplicateCheck] = useState<DuplicateCheck | null>(null);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState('');
  const [equipmentId, setEquipmentId] = useState<string | null>(null);
  const [location, setLocation] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<'low' | 'normal' | 'high' | 'urgent'>('normal');

  // Fetch prefill data on mount
  useEffect(() => {
    fetchPrefillData();
  }, [faultId]);

  const fetchPrefillData = async () => {
    try {
      setStep('loading');

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(
        `/api/v1/actions/create_work_order_from_fault/prefill?fault_id=${faultId}`,
        {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch prefill data');
      }

      const data = await response.json();

      if (data.status === 'error') {
        throw new Error(data.message);
      }

      // Set form values from prefill
      const prefill = data.prefill_data;
      setPrefillData(prefill);
      setTitle(prefill.title);
      setEquipmentId(prefill.equipment_id);
      setLocation(prefill.location);
      setDescription(prefill.description);
      setPriority(prefill.priority);

      // Check for duplicate
      setDuplicateCheck(data.duplicate_check);

      if (data.duplicate_check.has_duplicate) {
        setStep('duplicate_warning');
      } else {
        setStep('form');
      }

    } catch (err) {
      console.error('Prefill fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load form');
      setStep('error');
    }
  };

  const handleNext = async () => {
    try {
      // Validate form
      if (!title.trim()) {
        setError('Title is required');
        return;
      }

      if (!equipmentId) {
        setError('Equipment is required');
        return;
      }

      // Fetch preview
      setStep('loading');

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        throw new Error('Not authenticated');
      }

      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        throw new Error('User not found');
      }

      // Get yacht_id from user metadata
      const yachtId = user.user_metadata?.yacht_id || '';

      const response = await fetch(
        `/api/v1/actions/create_work_order_from_fault/preview`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            context: {
              yacht_id: yachtId,
              user_id: user.id,
            },
            payload: {
              fault_id: faultId,
              title,
              equipment_id: equipmentId,
              location,
              description,
              priority,
            },
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to generate preview');
      }

      const data = await response.json();

      if (data.status === 'error') {
        throw new Error(data.message);
      }

      setPreviewData(data.preview);
      setStep('preview');

    } catch (err) {
      console.error('Preview error:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate preview');
      setStep('error');
    }
  };

  const handleSignAndCreate = async () => {
    try {
      setStep('signing');

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        throw new Error('Not authenticated');
      }

      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        throw new Error('User not found');
      }

      const yachtId = user.user_metadata?.yacht_id || '';

      // Create signature
      const signature = {
        user_id: user.id,
        timestamp: new Date().toISOString(),
      };

      // Execute action
      const response = await fetch('/api/v1/actions/execute', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'create_work_order_from_fault',
          context: {
            yacht_id: yachtId,
            user_id: user.id,
          },
          payload: {
            fault_id: faultId,
            title,
            equipment_id: equipmentId,
            location,
            description,
            priority,
            signature,
            override_duplicate: false,
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create work order');
      }

      const data = await response.json();

      if (data.status === 'error') {
        throw new Error(data.message);
      }

      // Success!
      const workOrderId = data.result.work_order.id;
      setStep('success');

      // Navigate to work order detail after 1 second
      setTimeout(() => {
        onSuccess(workOrderId);
        router.push(`/work-orders/${workOrderId}`);
      }, 1000);

    } catch (err) {
      console.error('Execute error:', err);
      setError(err instanceof Error ? err.message : 'Failed to create work order');
      setStep('error');
    }
  };

  const handleOverrideDuplicate = () => {
    setStep('form');
  };

  const handleViewExisting = () => {
    if (duplicateCheck?.existing_wo) {
      router.push(`/work-orders/${duplicateCheck.existing_wo.id}`);
    }
  };

  // Render functions
  const renderLoading = () => (
    <div className="flex items-center justify-center p-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      <span className="ml-3 text-gray-600">Loading...</span>
    </div>
  );

  const renderDuplicateWarning = () => (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Work Order Already Exists</h2>
      <p className="text-gray-600 mb-4">
        A work order for this fault already exists:
      </p>

      {duplicateCheck?.existing_wo && (
        <div className="bg-gray-50 p-4 rounded mb-6">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-gray-600">Work Order:</div>
            <div className="font-medium">{duplicateCheck.existing_wo.number}</div>

            <div className="text-gray-600">Status:</div>
            <div className="font-medium capitalize">{duplicateCheck.existing_wo.status}</div>

            {duplicateCheck.existing_wo.assigned_to && (
              <>
                <div className="text-gray-600">Assigned:</div>
                <div className="font-medium">{duplicateCheck.existing_wo.assigned_to}</div>
              </>
            )}

            <div className="text-gray-600">Created:</div>
            <div className="font-medium">{duplicateCheck.existing_wo.days_ago} days ago</div>
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={handleViewExisting}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          View Existing WO
        </button>
        <button
          onClick={handleOverrideDuplicate}
          className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors"
        >
          Create New Anyway
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          Cancel
        </button>
      </div>
    </div>
  );

  const renderForm = () => (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-6">Create Work Order</h2>

      <div className="space-y-4">
        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Title *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Work order title"
          />
        </div>

        {/* Equipment (read-only, pre-filled) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Equipment *
          </label>
          <input
            type="text"
            value={prefillData?.equipment_name || ''}
            disabled
            className="w-full px-3 py-2 border border-gray-300 rounded bg-gray-50 text-gray-600"
          />
        </div>

        {/* Location */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Location
          </label>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Physical location"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Description of issue and work needed"
          />
        </div>

        {/* Priority */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Priority
          </label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as any)}
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 text-red-700 rounded">
          {error}
        </div>
      )}

      <div className="flex gap-3 mt-6">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          Cancel
        </button>
        <button
          onClick={handleNext}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Next
        </button>
      </div>
    </div>
  );

  const renderPreview = () => (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Review Work Order</h2>

      <p className="text-gray-600 mb-6">
        {previewData?.summary || 'You are about to create:'}
      </p>

      {/* Changes */}
      {previewData?.changes && (
        <div className="bg-gray-50 p-4 rounded mb-6">
          <h3 className="font-medium mb-3">Work Order</h3>
          <div className="space-y-2 text-sm">
            {Object.entries(previewData.changes).map(([key, value]) => (
              <div key={key} className="grid grid-cols-3 gap-2">
                <div className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</div>
                <div className="col-span-2 font-medium">{value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Side Effects */}
      {previewData?.side_effects && previewData.side_effects.length > 0 && (
        <div className="mb-6">
          <h3 className="font-medium mb-2 text-sm text-gray-700">Side Effects:</h3>
          <ul className="text-sm text-gray-600 space-y-1">
            {previewData.side_effects.map((effect, index) => (
              <li key={index} className="flex items-start">
                <span className="mr-2">ℹ️</span>
                <span>{effect}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => setStep('form')}
          className="px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          Back
        </button>
        <button
          onClick={handleSignAndCreate}
          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Sign & Create
        </button>
      </div>
    </div>
  );

  const renderSuccess = () => (
    <div className="p-6 bg-white rounded-lg shadow text-center">
      <div className="text-green-600 text-5xl mb-4">✓</div>
      <h2 className="text-xl font-semibold mb-2">Work Order Created</h2>
      <p className="text-gray-600">Redirecting to work order...</p>
    </div>
  );

  const renderError = () => (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-semibold text-red-600 mb-4">Error</h2>
      <p className="text-gray-700 mb-6">{error}</p>
      <button
        onClick={onCancel}
        className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
      >
        Close
      </button>
    </div>
  );

  // Main render
  return (
    <div className="max-w-2xl mx-auto">
      {step === 'loading' && renderLoading()}
      {step === 'duplicate_warning' && renderDuplicateWarning()}
      {step === 'form' && renderForm()}
      {step === 'preview' && renderPreview()}
      {step === 'signing' && renderLoading()}
      {step === 'success' && renderSuccess()}
      {step === 'error' && renderError()}
    </div>
  );
}
