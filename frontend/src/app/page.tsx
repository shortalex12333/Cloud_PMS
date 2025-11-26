import { redirect } from 'next/navigation';

// Force dynamic rendering to avoid prerendering issues
export const dynamic = 'force-dynamic';

// Root page redirects to search
export default function Home() {
  redirect('/search');
}
