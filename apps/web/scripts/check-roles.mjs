// Check test user roles in crew_members table
import { createClient } from '@supabase/supabase-js';

// Main test tenant
const supabaseUrl = 'https://qvzmkaamzaqxpzbewjxe.supabase.co';
// Use anon key for RLS-enabled query (service key was invalid)
const anonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzcxMjc2NjksImV4cCI6MjA1MjcwMzY2OX0.z5Y2HG05sDq9VWzPNEpCf22m2gvDZGiYqPLESjlCk90';
// Service key for direct DB access
const serviceKey = anonKey; // Will try anon first

const supabase = createClient(supabaseUrl, serviceKey);

const testUsers = [
  { name: 'captain', id: 'a35cad0b-02ff-4287-b6e4-17c96fa6a424', email: 'x@alex-short.com' },
  { name: 'hod', id: '05a488fd-e099-4d18-bf86-d87afba4fcdf', email: 'hod.test@alex-short.com' },
  { name: 'crew', id: '57e82f78-0a2d-4a7c-a428-6287621d06c5', email: 'crew.test@alex-short.com' },
];

async function main() {
  console.log('Checking test user roles in crew_members table:\n');

  for (const user of testUsers) {
    const { data, error } = await supabase
      .from('crew_members')
      .select('user_id, role, job_title, vessel_id')
      .eq('user_id', user.id);

    if (error) {
      console.log(user.name.toUpperCase() + ' (' + user.email + '): ERROR - ' + error.message);
    } else if (data && data.length > 0) {
      console.log(user.name.toUpperCase() + ' (' + user.email + '):');
      for (const row of data) {
        console.log('  - role: ' + row.role + ', job_title: ' + row.job_title + ', vessel: ' + row.vessel_id);
      }
    } else {
      console.log(user.name.toUpperCase() + ' (' + user.email + '): NOT FOUND in crew_members');
    }
  }
}

main().catch(console.error);
