import { redirect } from 'next/navigation';

// Force dynamic rendering to avoid prerendering issues
export const dynamic = 'force-dynamic';

// Root page ALWAYS redirects to login first
// Users must authenticate before accessing any other page
export default function Home() {
  redirect('/login');
}
