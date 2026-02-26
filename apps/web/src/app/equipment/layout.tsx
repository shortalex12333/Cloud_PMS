import { DomainProvider } from '@/lib/domain/context';

export default function EquipmentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DomainProvider route="/equipment">
      {children}
    </DomainProvider>
  );
}
