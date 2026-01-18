'use client';

import { useState, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { formatDate } from '@/lib/utils';
import {
  useRecord,
  useModelSchema,
  useUpdateRecord,
  useDeleteRecord,
} from '@/hooks/useApi';
import { useToast } from '@/components/ui/Toast';
import { PageHeader } from '@/components/layout/PageHeader';
import type { BreadcrumbItem } from '@/components/layout/Breadcrumb';
import { RecordForm, type FormMode } from '@/components/data/RecordForm';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@/components/ui/Modal';
import { Skeleton } from '@/components/ui/Loading';
import type { ModelRecord, SchemaProperty } from '@/types';

// ============================================================================
// Types
// ============================================================================

interface RecordDetailPageProps {
  params: {
    model: string;
    id: string;
  };
}

interface AuditLogEntry {
  id: string;
  action: string;
  timestamp: string;
  user: string | null;
  changes?: Record<string, { old: unknown; new: unknown }>;
}

interface RelatedRecordInfo {
  model: string;
  id: string | number;
  label: string;
  href: string;
}

// ============================================================================
// Icons
// ============================================================================

const EditIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
  </svg>
);

const TrashIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polyline points="3,6 5,6 21,6" />
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    <line x1="10" y1="11" x2="10" y2="17" />
    <line x1="14" y1="11" x2="14" y2="17" />
  </svg>
);

const BackIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <line x1="19" y1="12" x2="5" y2="12" />
    <polyline points="12,19 5,12 12,5" />
  </svg>
);

const LinkIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
  </svg>
);

const ClockIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="10" />
    <polyline points="12,6 12,12 16,14" />
  </svg>
);

const UserIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Formats a model name for display (e.g., "user_profile" -> "User Profile").
 */
function formatModelName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/**
 * Gets a display title for a record based on common field patterns.
 */
function getRecordTitle(record: ModelRecord, schema: { properties: Record<string, SchemaProperty> }): string {
  const titleFields = ['name', 'title', 'label', 'email', 'username', 'slug'];

  for (const field of titleFields) {
    if (record[field] && typeof record[field] === 'string') {
      return record[field] as string;
    }
  }

  // Fallback to ID or first string field
  if (record['id'] !== undefined) {
    return `Record #${record['id']}`;
  }

  const firstStringField = Object.entries(schema.properties).find(
    ([key, prop]) => prop.type === 'string' && record[key]
  );

  if (firstStringField) {
    return String(record[firstStringField[0]]);
  }

  return 'Record';
}

/**
 * Formats a value for display based on its type.
 */
function formatDisplayValue(value: unknown, property?: SchemaProperty): string {
  if (value === null || value === undefined) {
    return '-';
  }

  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No';
  }

  if (property?.format === 'date' && typeof value === 'string') {
    return formatDate(value);
  }

  if (property?.format === 'date-time' && typeof value === 'string') {
    return formatDate(value, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(', ') : '-';
  }

  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2);
  }

  return String(value);
}

/**
 * Extracts related records from record data based on schema.
 */
function extractRelatedRecords(
  record: ModelRecord,
  schema: { properties: Record<string, SchemaProperty> }
): RelatedRecordInfo[] {
  const related: RelatedRecordInfo[] = [];

  for (const [key, property] of Object.entries(schema.properties)) {
    // Check for relationship patterns (foreign keys, references)
    if (
      key.endsWith('_id') ||
      property.format === 'relation' ||
      (property.description?.toLowerCase().includes('foreign key'))
    ) {
      const relatedModel = key.replace(/_id$/, '');
      const relatedId = record[key];

      if (relatedId !== null && relatedId !== undefined) {
        related.push({
          model: relatedModel,
          id: relatedId as string | number,
          label: `${formatModelName(relatedModel)} #${relatedId}`,
          href: `/models/${relatedModel}/${relatedId}`,
        });
      }
    }
  }

  return related;
}

// ============================================================================
// Sub-Components
// ============================================================================

interface FieldDisplayProps {
  name: string;
  value: unknown;
  property: SchemaProperty;
}

function FieldDisplay({ name, value, property }: FieldDisplayProps) {
  const label = property.title || formatModelName(name);
  const displayValue = formatDisplayValue(value, property);
  const isLongContent = typeof displayValue === 'string' && displayValue.length > 100;

  return (
    <div className={cn('py-3', isLongContent && 'col-span-full')}>
      <dt className="text-sm font-medium text-[var(--color-muted)] mb-1">
        {label}
      </dt>
      <dd
        className={cn(
          'text-sm text-[var(--color-foreground)]',
          isLongContent && 'whitespace-pre-wrap break-words',
          property.type === 'boolean' && (
            value
              ? 'text-[var(--color-success)]'
              : 'text-[var(--color-muted)]'
          )
        )}
      >
        {displayValue}
      </dd>
    </div>
  );
}

interface RelatedRecordsSectionProps {
  records: RelatedRecordInfo[];
}

function RelatedRecordsSection({ records }: RelatedRecordsSectionProps) {
  if (records.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <LinkIcon className="h-4 w-4 text-[var(--color-muted)]" />
          <h3 className="text-sm font-medium text-[var(--color-foreground)]">
            Related Records
          </h3>
        </div>
      </CardHeader>
      <CardBody className="p-0">
        <ul className="divide-y divide-[var(--color-border)]">
          {records.map((related) => (
            <li key={`${related.model}-${related.id}`}>
              <Link
                href={related.href}
                className={cn(
                  'block px-6 py-3',
                  'hover:bg-[var(--color-card-hover)]',
                  'transition-colors duration-150'
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[var(--color-foreground)]">
                    {related.label}
                  </span>
                  <span className="text-xs text-[var(--color-muted)]">
                    {formatModelName(related.model)}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

interface AuditLogSectionProps {
  entries: AuditLogEntry[];
  isLoading?: boolean;
}

function AuditLogSection({ entries, isLoading }: AuditLogSectionProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ClockIcon className="h-4 w-4 text-[var(--color-muted)]" />
            <h3 className="text-sm font-medium text-[var(--color-foreground)]">
              Activity Log
            </h3>
          </div>
        </CardHeader>
        <CardBody>
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex gap-3">
                <Skeleton variant="circular" width={32} height={32} />
                <div className="flex-1 space-y-2">
                  <Skeleton variant="text" width="60%" />
                  <Skeleton variant="text" width="40%" />
                </div>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>
    );
  }

  if (entries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ClockIcon className="h-4 w-4 text-[var(--color-muted)]" />
            <h3 className="text-sm font-medium text-[var(--color-foreground)]">
              Activity Log
            </h3>
          </div>
        </CardHeader>
        <CardBody>
          <p className="text-sm text-[var(--color-muted)] text-center py-4">
            No activity recorded for this record.
          </p>
        </CardBody>
      </Card>
    );
  }

  const actionColors: Record<string, string> = {
    create: 'text-[var(--color-success)]',
    update: 'text-[var(--color-info)]',
    delete: 'text-[var(--color-error)]',
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <ClockIcon className="h-4 w-4 text-[var(--color-muted)]" />
          <h3 className="text-sm font-medium text-[var(--color-foreground)]">
            Activity Log
          </h3>
        </div>
      </CardHeader>
      <CardBody className="p-0">
        <ul className="divide-y divide-[var(--color-border)]">
          {entries.map((entry) => (
            <li key={entry.id} className="px-6 py-3">
              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    'flex-shrink-0 w-8 h-8 rounded-full',
                    'bg-[var(--color-card-hover)]',
                    'flex items-center justify-center'
                  )}
                >
                  <UserIcon className="h-4 w-4 text-[var(--color-muted)]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">
                    <span className={cn('font-medium', actionColors[entry.action] || '')}>
                      {entry.action.charAt(0).toUpperCase() + entry.action.slice(1)}
                    </span>
                    {entry.user && (
                      <span className="text-[var(--color-muted)]">
                        {' '}by {entry.user}
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-[var(--color-muted)] mt-0.5">
                    {formatDate(entry.timestamp, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                  {entry.changes && Object.keys(entry.changes).length > 0 && (
                    <div className="mt-2 text-xs space-y-1">
                      {Object.entries(entry.changes).map(([field, change]) => (
                        <div key={field} className="text-[var(--color-muted)]">
                          <span className="font-medium">{formatModelName(field)}:</span>{' '}
                          <span className="line-through opacity-60">
                            {String(change.old)}
                          </span>{' '}
                          <span>{String(change.new)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isDeleting: boolean;
  recordTitle: string;
  modelName: string;
}

function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  isDeleting,
  recordTitle,
  modelName,
}: DeleteConfirmModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalHeader onClose={onClose}>Delete {modelName}</ModalHeader>
      <ModalBody>
        <p className="text-sm text-[var(--color-foreground)]">
          Are you sure you want to delete{' '}
          <span className="font-semibold">{recordTitle}</span>?
        </p>
        <p className="text-sm text-[var(--color-muted)] mt-2">
          This action cannot be undone. All data associated with this record
          will be permanently removed.
        </p>
      </ModalBody>
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={isDeleting}>
          Cancel
        </Button>
        <Button variant="danger" onClick={onConfirm} loading={isDeleting}>
          Delete
        </Button>
      </ModalFooter>
    </Modal>
  );
}

interface RecordDetailSkeletonProps {
  modelName: string;
}

function RecordDetailSkeleton({ modelName }: RecordDetailSkeletonProps) {
  return (
    <div className="space-y-6">
      <PageHeader
        title={modelName}
        subtitle="Loading record details..."
        breadcrumbs={[
          { label: 'Models', href: '/models' },
          { label: modelName, href: `/models/${modelName}` },
          { label: 'Loading...' },
        ]}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <Skeleton variant="text" width="30%" height={20} />
            </CardHeader>
            <CardBody>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="space-y-2">
                    <Skeleton variant="text" width="40%" height={14} />
                    <Skeleton variant="text" width="70%" height={16} />
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <Skeleton variant="text" width="50%" height={16} />
            </CardHeader>
            <CardBody>
              <div className="space-y-3">
                {Array.from({ length: 2 }).map((_, i) => (
                  <Skeleton key={i} variant="text" width="80%" />
                ))}
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}

interface NotFoundDisplayProps {
  modelName: string;
  recordId: string;
}

function NotFoundDisplay({ modelName, recordId }: NotFoundDisplayProps) {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Record Not Found"
        breadcrumbs={[
          { label: 'Models', href: '/models' },
          { label: formatModelName(modelName), href: `/models/${modelName}` },
          { label: recordId },
        ]}
      />

      <Card>
        <CardBody className="py-12 text-center">
          <div
            className={cn(
              'w-16 h-16 mx-auto mb-4 rounded-full',
              'bg-[var(--color-card-hover)]',
              'flex items-center justify-center'
            )}
          >
            <svg
              className="h-8 w-8 text-[var(--color-muted)]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M16 16s-1.5-2-4-2-4 2-4 2" />
              <line x1="9" y1="9" x2="9.01" y2="9" />
              <line x1="15" y1="9" x2="15.01" y2="9" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
            Record Not Found
          </h2>
          <p className="text-sm text-[var(--color-muted)] mb-6 max-w-md mx-auto">
            The {formatModelName(modelName)} record with ID {recordId} could not
            be found. It may have been deleted or you may not have permission to
            view it.
          </p>
          <Link href={`/models/${modelName}`}>
            <Button variant="secondary" leftIcon={<BackIcon className="h-4 w-4" />}>
              Back to {formatModelName(modelName)} List
            </Button>
          </Link>
        </CardBody>
      </Card>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Record Detail Page
 *
 * Displays a single record with view/edit modes, delete confirmation,
 * related records, and audit log.
 */
export default function RecordDetailPage({ params }: RecordDetailPageProps) {
  const { model, id } = params;
  const router = useRouter();
  const { addToast } = useToast();

  // State
  const [mode, setMode] = useState<FormMode>('view');
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});

  // Data fetching
  const {
    data: record,
    isLoading: isLoadingRecord,
    error: recordError,
    refetch: refetchRecord,
  } = useRecord<ModelRecord>(model, id);

  const {
    data: schema,
    isLoading: isLoadingSchema,
  } = useModelSchema(model);

  // Mutations
  const updateMutation = useUpdateRecord<ModelRecord>(model, {
    onSuccess: () => {
      addToast({
        variant: 'success',
        title: 'Record Updated',
        description: 'The record has been saved successfully.',
      });
      setMode('view');
      setServerErrors({});
      refetchRecord();
    },
    onError: (error) => {
      addToast({
        variant: 'error',
        title: 'Update Failed',
        description: error.message || 'Failed to update the record.',
      });
      // Handle field-level errors if available
      if (error.response?.extra?.['errors']) {
        const fieldErrors: Record<string, string> = {};
        const errors = error.response.extra['errors'] as Array<{ field: string; message: string }>;
        for (const err of errors) {
          fieldErrors[err.field] = err.message;
        }
        setServerErrors(fieldErrors);
      }
    },
  });

  const deleteMutation = useDeleteRecord(model, {
    onSuccess: () => {
      addToast({
        variant: 'success',
        title: 'Record Deleted',
        description: 'The record has been deleted successfully.',
      });
      router.push(`/models/${model}`);
    },
    onError: (error) => {
      addToast({
        variant: 'error',
        title: 'Delete Failed',
        description: error.message || 'Failed to delete the record.',
      });
      setShowDeleteModal(false);
    },
  });

  // Computed values
  const modelDisplayName = formatModelName(model);

  const recordTitle = useMemo(() => {
    if (!record || !schema) return `Record #${id}`;
    return getRecordTitle(record, schema);
  }, [record, schema, id]);

  const relatedRecords = useMemo(() => {
    if (!record || !schema) return [];
    return extractRelatedRecords(record, schema);
  }, [record, schema]);

  // Mock audit log - in production, fetch from API
  const auditLog = useMemo<AuditLogEntry[]>(() => {
    if (!record) return [];

    const entries: AuditLogEntry[] = [];

    // Check for created_at timestamp
    if (record['created_at']) {
      entries.push({
        id: 'created',
        action: 'create',
        timestamp: String(record['created_at']),
        user: record['created_by'] ? String(record['created_by']) : null,
      });
    }

    // Check for updated_at timestamp
    if (record['updated_at'] && record['updated_at'] !== record['created_at']) {
      entries.push({
        id: 'updated',
        action: 'update',
        timestamp: String(record['updated_at']),
        user: record['updated_by'] ? String(record['updated_by']) : null,
      });
    }

    return entries.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [record]);

  // Breadcrumbs
  const breadcrumbs: BreadcrumbItem[] = useMemo(() => [
    { label: 'Models', href: '/models' },
    { label: modelDisplayName, href: `/models/${model}` },
    { label: recordTitle },
  ], [model, modelDisplayName, recordTitle]);

  // Handlers
  const handleEdit = useCallback(() => {
    setMode('edit');
    setServerErrors({});
  }, []);

  const handleCancel = useCallback(() => {
    setMode('view');
    setServerErrors({});
  }, []);

  const handleSubmit = useCallback(
    async (values: ModelRecord) => {
      await updateMutation.mutateAsync({ id, data: values });
    },
    [updateMutation, id]
  );

  const handleDelete = useCallback(() => {
    setShowDeleteModal(true);
  }, []);

  const handleConfirmDelete = useCallback(() => {
    deleteMutation.mutate({ id });
  }, [deleteMutation, id]);

  const handleCloseDeleteModal = useCallback(() => {
    setShowDeleteModal(false);
  }, []);

  // Loading state
  const isLoading = isLoadingRecord || isLoadingSchema;

  if (isLoading) {
    return <RecordDetailSkeleton modelName={modelDisplayName} />;
  }

  // Not found state
  if (recordError || !record || !schema) {
    return <NotFoundDisplay modelName={model} recordId={id} />;
  }

  // Separate fields into groups
  const orderedFields = Object.entries(schema.properties).sort(([aName], [bName]) => {
    const requiredSet = new Set(schema.required);
    const aRequired = requiredSet.has(aName);
    const bRequired = requiredSet.has(bName);
    if (aRequired && !bRequired) return -1;
    if (!aRequired && bRequired) return 1;
    return aName.localeCompare(bName);
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title={recordTitle}
        subtitle={`${modelDisplayName} Details`}
        breadcrumbs={breadcrumbs}
        actions={
          mode === 'view' ? (
            <div className="flex items-center gap-3">
              <Link href={`/models/${model}`}>
                <Button
                  variant="secondary"
                  size="sm"
                  leftIcon={<BackIcon className="h-4 w-4" />}
                >
                  Back to List
                </Button>
              </Link>
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<EditIcon className="h-4 w-4" />}
                onClick={handleEdit}
              >
                Edit
              </Button>
              <Button
                variant="danger"
                size="sm"
                leftIcon={<TrashIcon className="h-4 w-4" />}
                onClick={handleDelete}
              >
                Delete
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Button variant="secondary" size="sm" onClick={handleCancel}>
                Cancel
              </Button>
            </div>
          )
        }
      />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Record Details / Edit Form */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <h2 className="text-base font-medium text-[var(--color-foreground)]">
                {mode === 'view' ? 'Record Details' : 'Edit Record'}
              </h2>
            </CardHeader>
            <CardBody>
              {mode === 'view' ? (
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1">
                  {orderedFields.map(([name, property]) => (
                    <FieldDisplay
                      key={name}
                      name={name}
                      value={record[name]}
                      property={property}
                    />
                  ))}
                </dl>
              ) : (
                <RecordForm
                  schema={schema}
                  initialValues={record}
                  onSubmit={handleSubmit}
                  onCancel={handleCancel}
                  isSubmitting={updateMutation.isPending}
                  mode="edit"
                  errors={serverErrors}
                />
              )}
            </CardBody>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Related Records */}
          <RelatedRecordsSection records={relatedRecords} />

          {/* Audit Log */}
          <AuditLogSection entries={auditLog} />
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={showDeleteModal}
        onClose={handleCloseDeleteModal}
        onConfirm={handleConfirmDelete}
        isDeleting={deleteMutation.isPending}
        recordTitle={recordTitle}
        modelName={modelDisplayName}
      />
    </div>
  );
}
