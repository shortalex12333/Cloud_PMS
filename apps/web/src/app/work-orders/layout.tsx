import { DomainProvider } from '@/lib/domain/context';

export default function WorkOrdersLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DomainProvider route="/work-orders">
      {children}
    </DomainProvider>
  );
}
