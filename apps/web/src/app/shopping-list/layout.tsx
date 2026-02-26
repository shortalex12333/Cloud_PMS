import { DomainProvider } from '@/lib/domain/context';

export default function ShoppingListLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <DomainProvider route="/shopping-list">
      {children}
    </DomainProvider>
  );
}
