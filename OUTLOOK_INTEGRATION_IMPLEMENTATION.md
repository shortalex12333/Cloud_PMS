# Outlook Integration Implementation

Complete implementation of Microsoft Outlook OAuth integration for CelesteOS, copied and adapted from `c.os.4.1` repository.

## 🎯 Objective

Add Outlook integration to CelesteOS with a `/settings` page where users can connect their Microsoft Outlook account. The implementation follows the existing OAuth flow from `c.os.4.1` repo with these key principles:

- **Frontend never sees tokens** - Only connection status
- **Tokens stored backend-only** - In Supabase with RLS
- **n8n workflow integration** - Workflows can fetch tokens via service key
- **Copy existing logic** - Don't reinvent, reuse working code

## 📁 Files Created/Modified

### Backend (FastAPI)

#### 1. Database Migration
**File**: `cloud/supabase/migrations/003_integration_tokens.sql`

Creates `integration_tokens` table for storing OAuth tokens:

```sql
CREATE TABLE integration_tokens (
    user_id UUID NOT NULL,
    provider TEXT NOT NULL CHECK (provider IN ('microsoft', 'google', 'dropbox')),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    provider_user_id TEXT,
    provider_email TEXT,
    display_name TEXT,
    scopes TEXT[],
    UNIQUE(user_id, provider)
);
```

**Key Features:**
- One integration per user per provider
- RLS policies for user isolation
- Service role has full access (for n8n)
- Auto-update `updated_at` trigger
- Helper function `user_has_integration(user_id, provider)`

#### 2. API Models
**File**: `cloud/api/app/models/integrations.py`

Pydantic models for API requests/responses:

- `OutlookAuthUrlResponse` - Contains OAuth URL
- `OutlookStatusResponse` - Connection status (never includes tokens)
- `IntegrationTokenData` - Internal token storage model

#### 3. API Endpoints
**File**: `cloud/api/app/api/v1/endpoints/integrations.py`

**Copied from**: `c.os.4.1/server/routes/emailRoutes.ts`

Four endpoints:

1. **GET /v1/integrations/outlook/auth-url**
   - Generates Microsoft OAuth URL
   - Includes state parameter with user_id + CSRF token
   - Frontend uses this to open OAuth popup

2. **GET /v1/integrations/outlook/callback**
   - Handles OAuth redirect from Microsoft
   - Exchanges code for access/refresh tokens
   - Fetches user profile from Microsoft Graph
   - Stores tokens in `integration_tokens` table
   - Returns HTML that closes popup and notifies parent window

3. **GET /v1/integrations/outlook/status**
   - Returns connection status for current user
   - **Never returns tokens** - only connection metadata
   - Frontend uses this to show "Connected ✓" or "Connect" button

4. **DELETE /v1/integrations/outlook/disconnect**
   - Deletes user's integration tokens
   - Allows user to disconnect Outlook

**Microsoft OAuth Config** (copied from `c.os.4.1`):
```python
MICROSOFT_CONFIG = {
    "tenant_id": "common",  # Multitenant
    "client_id": "41f6dc82-8127-4330-97e0-c6b26e6aa967",
    "client_secret": "<your-azure-client-secret>",  # TODO: Set in env var
    "redirect_uri": "https://api.celeste7.ai/v1/integrations/outlook/callback",
    "scopes": [
        "https://graph.microsoft.com/Mail.Read",
        "https://graph.microsoft.com/User.Read",
        "https://graph.microsoft.com/MailboxSettings.Read",
        "offline_access"
    ]
}
```

#### 4. Router Registration
**File**: `cloud/api/app/api/v1/__init__.py`

Added integrations router to API:
```python
from app.api.v1.endpoints import ..., integrations

api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
```

### Frontend (Next.js)

#### Directory Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout
│   │   ├── page.tsx             # Home page
│   │   ├── globals.css          # Global styles
│   │   └── settings/
│   │       └── page.tsx         # Settings page with Outlook integration
│   ├── hooks/
│   │   ├── useAuth.ts           # Supabase authentication
│   │   └── useOutlookIntegration.ts  # Outlook OAuth flow
│   └── lib/
│       └── supabase.ts          # Supabase client
├── package.json
├── next.config.js
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── .env.example
└── README.md
```

#### 1. Authentication Hook
**File**: `frontend/src/hooks/useAuth.ts`

Provides current user context using Supabase Auth:

```typescript
export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Get session and listen for auth changes
  // ...

  return { user, loading };
}
```

#### 2. Outlook Integration Hook
**File**: `frontend/src/hooks/useOutlookIntegration.ts`

**Copied from**: `c.os.4.1/client/services/outlookService.ts`

Manages Outlook OAuth flow:

```typescript
export function useOutlookIntegration(userId?: string) {
  const [status, setStatus] = useState<OutlookStatus | null>(null);

  const connectOutlook = async () => {
    // 1. Get auth URL from backend
    // 2. Open OAuth popup
    // 3. Listen for success message
    // 4. Refresh status
  };

  const disconnectOutlook = async () => {
    // Call DELETE /integrations/outlook/disconnect
  };

  return { status, loading, error, connectOutlook, disconnectOutlook };
}
```

**Key Features:**
- Fetches connection status on mount
- Opens OAuth popup window
- Listens for `MICROSOFT_AUTH_SUCCESS` message
- Handles popup blocking (fallback to same-window redirect)
- Never stores or displays tokens

#### 3. Settings Page
**File**: `frontend/src/app/settings/page.tsx`

UI for managing integrations:

```typescript
export default function SettingsPage() {
  const { user } = useAuth();
  const { status, connectOutlook, disconnectOutlook } = useOutlookIntegration(user?.id);

  return (
    <div>
      <h1>Settings</h1>

      {/* Outlook Integration Card */}
      {status?.connected ? (
        <>
          <span>Connected ✓</span>
          <p>Email: {status.provider_email}</p>
          <button onClick={disconnectOutlook}>Disconnect</button>
        </>
      ) : (
        <button onClick={connectOutlook}>Connect Outlook</button>
      )}
    </div>
  );
}
```

#### 4. Configuration Files

**package.json**:
- Next.js 14.1.0
- React 18.2.0
- Supabase SSR 0.1.0
- TypeScript 5
- Tailwind CSS 3.4.0

**next.config.js**:
```javascript
env: {
  NEXT_PUBLIC_API_URL: 'https://api.celeste7.ai/v1',
  NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
  NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
}
```

**.env.example**:
```
NEXT_PUBLIC_API_URL=https://api.celeste7.ai/v1
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## 🔐 Security Architecture

### Token Isolation

1. **Frontend**: Only sees connection status (`connected: true/false`)
2. **Backend**: Stores tokens in database with RLS
3. **Database**: User can only access their own tokens
4. **n8n**: Can fetch tokens using service role key

### Row-Level Security (RLS)

```sql
-- Users can only access their own tokens
CREATE POLICY "Users can access own integration tokens"
    ON integration_tokens
    FOR ALL
    USING (user_id = auth.uid());

-- Service role has full access (for n8n workflows)
CREATE POLICY "Service role has full access to integration tokens"
    ON integration_tokens
    FOR ALL
    TO service_role
    USING (true);
```

### OAuth Flow Security

1. **State Parameter**: Includes user_id + CSRF token
2. **HTTPS Only**: All OAuth callbacks use HTTPS
3. **Token Expiry**: Tokens have expiration timestamps
4. **Refresh Tokens**: Stored for token renewal

## 🔄 OAuth Flow

### Step-by-Step

1. **User clicks "Connect Outlook"**
   - Frontend: `useOutlookIntegration.connectOutlook()`
   - Calls: `GET /v1/integrations/outlook/auth-url`

2. **Backend generates OAuth URL**
   - Creates state: `user_id:csrf_token`
   - Returns Microsoft authorization URL
   - Frontend opens URL in popup window

3. **User authenticates with Microsoft**
   - Microsoft login page
   - User grants permissions
   - Microsoft redirects to callback URL

4. **Callback handler processes authorization**
   - Backend: `GET /v1/integrations/outlook/callback`
   - Exchanges code for tokens (POST to Microsoft token endpoint)
   - Fetches user profile from Microsoft Graph API
   - Stores tokens in `integration_tokens` table

5. **Success page closes popup**
   - Returns HTML with `window.opener.postMessage()`
   - Sends `MICROSOFT_AUTH_SUCCESS` message
   - Frontend receives message and refreshes status

6. **Status updates**
   - Frontend calls `GET /v1/integrations/outlook/status`
   - UI shows "Connected ✓" with user email

### Sequence Diagram

```
Frontend          Backend           Microsoft         Database
   |                 |                   |                |
   |-- GET /auth-url -->                 |                |
   |<-- auth_url ---|                    |                |
   |                 |                   |                |
   |-- Open popup -->|                   |                |
   |                 |                   |                |
   |                 |<-- Redirect ------|                |
   |                 |                   |                |
   |                 |-- Exchange code --|-->             |
   |                 |<-- Tokens --------|                |
   |                 |                   |                |
   |                 |-- Graph API ------|-->             |
   |                 |<-- User info -----|                |
   |                 |                   |                |
   |                 |-- Insert tokens --|--------------->|
   |                 |                   |                |
   |<-- Success msg -|                   |                |
   |                 |                   |                |
   |-- GET /status --|                   |                |
   |<-- {connected} -|                   |                |
```

## 🔌 n8n Integration

n8n workflows can access user tokens to call Microsoft Graph API:

```javascript
// In n8n Code node
const supabase = require('@supabase/supabase-js').createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY  // Service role key
);

// Fetch user's Microsoft token
const { data: token } = await supabase
  .from('integration_tokens')
  .select('access_token, refresh_token, expires_at')
  .eq('user_id', userId)
  .eq('provider', 'microsoft')
  .single();

if (new Date(token.expires_at) < new Date()) {
  // Token expired - need to refresh
  // TODO: Implement token refresh logic
}

// Call Microsoft Graph API
const response = await fetch(
  'https://graph.microsoft.com/v1.0/me/messages',
  {
    headers: {
      'Authorization': `Bearer ${token.access_token}`,
      'Content-Type': 'application/json'
    }
  }
);

const emails = await response.json();
```

## 📝 Configuration Required

### Backend Environment Variables

Add to `cloud/api/.env`:

```bash
# Microsoft OAuth (required)
MICROSOFT_CLIENT_SECRET=<your-azure-client-secret>
```

**Important**: The client secret must be obtained from Azure Portal:
1. Go to Azure Portal → App Registrations
2. Find app: `41f6dc82-8127-4330-97e0-c6b26e6aa967`
3. Go to "Certificates & secrets"
4. Copy the client secret value
5. Set as environment variable

### Frontend Environment Variables

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=https://api.celeste7.ai/v1
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### Database Migration

Apply the migration:

```bash
# Using Supabase CLI
cd cloud/supabase
supabase db push

# Or apply directly in Supabase SQL Editor
# Copy contents of 003_integration_tokens.sql and run
```

## 🚀 Deployment

### Backend (FastAPI)

```bash
cd cloud/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export MICROSOFT_CLIENT_SECRET="<secret>"
export SUPABASE_URL="<url>"
export SUPABASE_SERVICE_KEY="<key>"

# Run server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run build
npm start
```

Or deploy to Vercel:

```bash
vercel deploy
```

## 🧪 Testing

### Manual Testing

1. **Navigate to settings page**:
   ```
   http://localhost:3000/settings
   ```

2. **Click "Connect Outlook"**:
   - Should open Microsoft login popup
   - Login with Microsoft account
   - Grant permissions
   - Popup should close automatically

3. **Verify connection**:
   - Status should show "Connected ✓"
   - Should display email and name
   - "Disconnect" button should appear

4. **Test disconnect**:
   - Click "Disconnect"
   - Status should change to "Not Connected"
   - "Connect Outlook" button should reappear

### API Testing

Test auth URL endpoint:

```bash
# Get auth URL (requires JWT token)
curl -X GET https://api.celeste7.ai/v1/integrations/outlook/auth-url \
  -H "Authorization: Bearer <your-jwt-token>"
```

Test status endpoint:

```bash
# Check connection status
curl -X GET https://api.celeste7.ai/v1/integrations/outlook/status \
  -H "Authorization: Bearer <your-jwt-token>"
```

## 🐛 Troubleshooting

### "Popup blocked" error
- **Cause**: Browser is blocking popups
- **Solution**: Allow popups for this site
- **Fallback**: Redirects in same window

### "Failed to get auth URL" error
- **Cause**: Backend not running or unreachable
- **Solution**: Check `NEXT_PUBLIC_API_URL` in `.env.local`
- **Verify**: `curl https://api.celeste7.ai/v1/health`

### "Token exchange failed" error
- **Cause**: Microsoft client secret not set
- **Solution**: Set `MICROSOFT_CLIENT_SECRET` in backend env
- **Verify**: Check backend logs for detailed error

### "Failed to store token" error
- **Cause**: Database migration not applied
- **Solution**: Apply migration `003_integration_tokens.sql`
- **Verify**: Check table exists in Supabase dashboard

### CORS errors
- **Cause**: Frontend calling backend from different origin
- **Solution**: Add frontend URL to CORS allowed origins in backend
- **File**: `cloud/api/main.py` - Update `CORS_ORIGINS` in settings

## 📚 References

### Source Code (c.os.4.1 repo)

- **Backend OAuth logic**: `server/routes/emailRoutes.ts`
  - Lines 14-28: Microsoft config
  - Lines 31-44: `generateAuthUrl()`
  - Lines 52-89: `/microsoft-auth` endpoint
  - Lines 289-447: `/auth/microsoft/callback` endpoint
  - Lines 459-587: `/user/:userId/status` endpoint

- **Frontend service**: `client/services/outlookService.ts`
  - Lines 7-75: `startOutlookAuth()` function
  - OAuth popup flow
  - Message listener for success

- **Database schema**: `supabase/migrations/20240924000008_critical_yacht_tables.sql`
  - Lines 1-14: `user_microsoft_tokens` table

### New Implementation (Cloud_PMS repo)

- **Backend**: `cloud/api/app/api/v1/endpoints/integrations.py`
- **Frontend**: `frontend/src/app/settings/page.tsx`
- **Hook**: `frontend/src/hooks/useOutlookIntegration.ts`
- **Migration**: `cloud/supabase/migrations/003_integration_tokens.sql`

### Microsoft Documentation

- [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/)
- [OAuth 2.0 in Microsoft Identity Platform](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow)
- [Microsoft Graph Mail API](https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview)

## ✅ Verification Checklist

- [x] Database migration created (`003_integration_tokens.sql`)
- [x] Backend API endpoints implemented (`integrations.py`)
- [x] Frontend hooks created (`useAuth.ts`, `useOutlookIntegration.ts`)
- [x] Settings page implemented (`/settings`)
- [x] OAuth flow copied from `c.os.4.1`
- [x] Microsoft config matches existing app registration
- [x] Tokens stored backend-only with RLS
- [x] Frontend never sees tokens
- [x] n8n can access tokens via service role
- [x] All dependencies added to requirements/package.json
- [x] Documentation created (README.md)

## 🎉 Next Steps

1. **Set Microsoft client secret** in backend environment
2. **Apply database migration** to Supabase
3. **Deploy backend** with updated code
4. **Deploy frontend** to Vercel or hosting platform
5. **Test OAuth flow** end-to-end
6. **Create n8n workflow** to consume Outlook tokens
7. **Implement token refresh logic** for expired tokens
8. **Add error monitoring** (Sentry, etc.)
9. **Add additional integrations** (Google, Dropbox, etc.)

## 📞 Support

For issues or questions:
- Check logs in backend (`cloud/api/logs/`)
- Check browser console for frontend errors
- Verify environment variables are set correctly
- Check Supabase dashboard for RLS policy issues

---

**Implementation Date**: 2025-11-20
**Source Repo**: `c.os.4.1` (https://github.com/shortalex12333/c.os.4.1)
**Target Repo**: `Cloud_PMS` (https://github.com/shortalex12333/Cloud_PMS)
**Branch**: `claude/add-file-reading-013P1WA2TehYr3YeKk1z9MEq`
