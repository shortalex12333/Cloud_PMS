import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.join(process.cwd(), '.env.e2e.local') });

const TENANT_URL = 'https://vzsohavtuotocgrfkfyd.supabase.co';
const TENANT_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk4MzYxNSwiZXhwIjoyMDc5NTU5NjE1fQ.vU1mNLvZoTwODBjkq38BKJL2uJJXk6Tq4DlM-tABEYY';
const CAPTAIN_USER_ID = 'b72c35ff-e309-4a19-a617-bfc706a78c0f';

async function checkAuthUsers() {
  const db = createClient(TENANT_URL, TENANT_KEY);

  console.log('\n=== Checking auth_users_profiles table ===\n');

  try {
    const { data, error } = await db
      .from('auth_users_profiles')
      .select('*')
      .limit(10);

    if (error) {
      console.error('Error querying auth_users_profiles:', error);
    } else {
      console.log(`Found ${data?.length || 0} profiles:`);
      data?.forEach((profile: any) => {
        console.log(`- ID: ${profile.user_id}, Email: ${profile.email || 'N/A'}, Role: ${profile.role || 'N/A'}`);
      });
    }

    // Check specifically for captain user
    console.log(`\n=== Checking for captain user ID: ${CAPTAIN_USER_ID} ===\n`);
    const { data: captainData, error: captainError } = await db
      .from('auth_users_profiles')
      .select('*')
      .eq('user_id', CAPTAIN_USER_ID);

    if (captainError) {
      console.error('Error:', captainError);
    } else {
      console.log('Captain profile found:', captainData?.length > 0 ? 'YES' : 'NO');
      if (captainData && captainData.length > 0) {
        console.log(JSON.stringify(captainData[0], null, 2));
      }
    }

  } catch (err) {
    console.error('FATAL:', err);
  }
}

checkAuthUsers();
