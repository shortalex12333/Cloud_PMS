import { DomainProvider } from '@/lib/domain/context';

export default function FaultsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DomainProvider route="/faults">
      {children}
    </DomainProvider>
  );
}
