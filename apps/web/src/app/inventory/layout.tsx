import { DomainProvider } from '@/lib/domain/context';

export default function InventoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DomainProvider route="/inventory">
      {children}
    </DomainProvider>
  );
}
