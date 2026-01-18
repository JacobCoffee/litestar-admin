'use client';

import Link from 'next/link';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Card, CardBody } from '@/components/ui/Card';

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

/**
 * Not found page for record detail routes.
 * Displayed when a record with the given ID cannot be found.
 */
export default function RecordNotFound() {
  return (
    <div className="space-y-6">
      <Card>
        <CardBody className="py-16 text-center">
          <div
            className={cn(
              'w-20 h-20 mx-auto mb-6 rounded-full',
              'bg-[var(--color-card-hover)]',
              'flex items-center justify-center'
            )}
          >
            <svg
              className="h-10 w-10 text-[var(--color-muted)]"
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
          <h1 className="text-2xl font-semibold text-[var(--color-foreground)] mb-3">
            Record Not Found
          </h1>
          <p className="text-[var(--color-muted)] mb-8 max-w-md mx-auto">
            The record you are looking for could not be found. It may have been
            deleted or you may not have permission to view it.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link href="/models">
              <Button
                variant="secondary"
                leftIcon={<BackIcon className="h-4 w-4" />}
              >
                Back to Models
              </Button>
            </Link>
            <Link href="/">
              <Button variant="primary">Go to Dashboard</Button>
            </Link>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
