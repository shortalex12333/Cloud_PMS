import { DomainProvider } from '@/lib/domain/context';

export default function ReceivingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DomainProvider route="/receiving">
      {children}
    </DomainProvider>
  );
}
