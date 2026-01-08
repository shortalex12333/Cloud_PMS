'use client';

import { ReactNode } from 'react';
import { usePathname } from 'next/navigation';

interface DashboardLayoutProps {
  children: ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname();

  const tabs = [
    { name: 'Overview', href: '/dashboard', active: pathname === '/dashboard' },
    { name: 'Equipment', href: '/dashboard/equipment', active: pathname === '/dashboard/equipment' },
    { name: 'Inventory', href: '/dashboard/inventory', active: pathname === '/dashboard/inventory' },
    { name: 'Work Orders', href: '/dashboard/work-orders', active: pathname === '/dashboard/work-orders' },
    { name: 'Predictive', href: '/dashboard/predictive', active: pathname === '/dashboard/predictive' },
    { name: 'Settings', href: '/dashboard/settings', active: pathname === '/dashboard/settings' },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold">Dashboard</h1>
              <p className="text-sm text-muted-foreground mt-1">
                HOD Overview & Configuration
              </p>
            </div>
            <a
              href="/search"
              className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              ← Back to Search
            </a>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="border-b border-border bg-card sticky top-[89px] z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex gap-6 text-sm overflow-x-auto">
            {tabs.map((tab) => (
              <a
                key={tab.name}
                href={tab.href}
                className={`py-3 border-b-2 transition-colors whitespace-nowrap ${
                  tab.active
                    ? 'border-primary font-medium text-foreground'
                    : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/50'
                }`}
              >
                {tab.name}
              </a>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
