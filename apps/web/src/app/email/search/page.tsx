/**
 * Email Search Page - Redirects to /email/inbox
 *
 * This route is deprecated. The canonical email interface is /email/inbox
 * which handles both inbox browsing and semantic search.
 */

import { redirect } from 'next/navigation';

export default function EmailSearchPage() {
  redirect('/email/inbox');
}
