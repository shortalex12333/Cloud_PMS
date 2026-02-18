import Link from 'next/link';

// Force dynamic rendering to avoid prerendering issues with auth context
export const dynamic = 'force-dynamic';

export default function NotFound() {
  return (
    <div className="spotlight-container">
      <div className="w-full max-w-md text-center">
        <div className="bg-surface-elevated border border-surface-border rounded-lg p-8">
          <h1 className="text-6xl font-bold text-txt-tertiary mb-4">404</h1>
          <h2 className="text-xl font-semibold mb-2">Page Not Found</h2>
          <p className="text-sm text-txt-secondary mb-6">
            The page you&apos;re looking for doesn&apos;t exist or has been moved.
          </p>
          <Link
            href="/"
            className="inline-block px-6 py-2 bg-brand-interactive text-txt-inverse rounded-md hover:bg-brand-hover font-medium"
          >
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}
