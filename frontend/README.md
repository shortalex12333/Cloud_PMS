# CelesteOS Frontend

Next.js frontend for CelesteOS yacht management system with Outlook integration.

## Features

- **Outlook Integration**: Connect Microsoft Outlook account for email ingestion
- **Settings UI**: Manage third-party integrations
- **Supabase Auth**: User authentication via Supabase

## Architecture

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── globals.css         # Global styles
│   │   └── settings/           # Settings page
│   │       └── page.tsx        # /settings - Outlook integration UI
│   ├── hooks/                  # React hooks
│   │   ├── useAuth.ts          # Supabase authentication hook
│   │   └── useOutlookIntegration.ts  # Outlook OAuth flow hook
│   └── lib/                    # Utilities
│       └── supabase.ts         # Supabase client
├── package.json
├── tsconfig.json
└── tailwind.config.ts
```

## Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

Create `.env.local`:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=https://api.celeste7.ai/v1

# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 3. Run Development Server

```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000)

### 4. Build for Production

```bash
npm run build
npm start
```

## Outlook Integration Flow

The Outlook integration follows the OAuth 2.0 flow copied from `c.os.4.1` repo:

### Frontend Flow

1. User clicks "Connect Outlook" button on `/settings` page
2. Frontend calls `GET /v1/integrations/outlook/auth-url`
3. Backend returns Microsoft OAuth URL
4. Frontend opens URL in popup window
5. User authenticates with Microsoft
6. Microsoft redirects to `/v1/integrations/outlook/callback`
7. Backend exchanges code for tokens, stores in `integration_tokens` table
8. Callback page sends success message to opener window
9. Frontend closes popup and refreshes connection status

### Security

- **Frontend NEVER sees tokens**: Only connection status (connected/not connected)
- **Tokens stored backend-only**: In `integration_tokens` table with RLS
- **Service role access**: n8n workflows can fetch tokens using service key
- **Per-user isolation**: Each user can only access their own tokens

## API Endpoints

All endpoints require authentication (JWT from Supabase).

### GET /v1/integrations/outlook/auth-url

Returns Microsoft OAuth URL for current user.

**Response:**
```json
{
  "auth_url": "https://login.microsoftonline.com/...",
  "state": "user_id:csrf_token"
}
```

### GET /v1/integrations/outlook/callback

OAuth callback handler (not called by frontend directly).

**Query Params:**
- `code`: Authorization code from Microsoft
- `state`: User ID + CSRF token

**Returns:** HTML page that closes popup and notifies parent window

### GET /v1/integrations/outlook/status

Check if current user has Outlook connected.

**Response:**
```json
{
  "connected": true,
  "provider_email": "user@example.com",
  "display_name": "John Doe",
  "connected_at": "2025-11-20T10:00:00Z"
}
```

### DELETE /v1/integrations/outlook/disconnect

Disconnect user's Outlook integration (delete tokens).

**Response:**
```json
{
  "success": true,
  "message": "Outlook disconnected successfully"
}
```

## n8n Integration

n8n workflows can access user tokens via service key:

```javascript
// In n8n Code node
const supabase = require('@supabase/supabase-js').createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_KEY
);

// Fetch user's Microsoft token
const { data, error } = await supabase
  .from('integration_tokens')
  .select('access_token, refresh_token, expires_at')
  .eq('user_id', userId)
  .eq('provider', 'microsoft')
  .single();

// Use token to call Microsoft Graph API
const graphResponse = await fetch('https://graph.microsoft.com/v1.0/me/messages', {
  headers: {
    'Authorization': `Bearer ${data.access_token}`
  }
});
```

## Microsoft App Configuration

The Microsoft OAuth app is already registered:

- **Client ID**: `41f6dc82-8127-4330-97e0-c6b26e6aa967`
- **Tenant**: `common` (multitenant)
- **Redirect URI**: `https://api.celeste7.ai/v1/integrations/outlook/callback`
- **Scopes**:
  - `Mail.Read`
  - `User.Read`
  - `MailboxSettings.Read`
  - `offline_access` (for refresh tokens)

**Important**: Client secret must be set in backend environment variable `MICROSOFT_CLIENT_SECRET`.

## Development

### Adding New Integrations

1. Add provider to `integration_tokens` table migration:
   ```sql
   CHECK (provider IN ('microsoft', 'google', 'your-new-provider'))
   ```

2. Create endpoint in `cloud/api/app/api/v1/endpoints/integrations.py`:
   ```python
   @router.get("/your-provider/auth-url")
   async def get_your_provider_auth_url(...):
       # Implementation
   ```

3. Add UI to `frontend/src/app/settings/page.tsx`

4. Create hook in `frontend/src/hooks/useYourProviderIntegration.ts`

## Troubleshooting

### "Popup blocked" error
- Browser is blocking popups
- Fallback: redirects in same window
- Solution: Allow popups for this site

### "Failed to get auth URL" error
- Backend is not running
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Verify API is accessible

### "Token exchange failed" error
- Microsoft client secret not configured
- Check backend logs for details
- Verify redirect URI matches Microsoft app registration

### "Failed to store token" error
- Database migration not applied
- Check Supabase connection
- Verify RLS policies allow service role access

## Related Files

**Backend:**
- `cloud/api/app/api/v1/endpoints/integrations.py` - API endpoints
- `cloud/api/app/models/integrations.py` - Pydantic models
- `cloud/supabase/migrations/003_integration_tokens.sql` - Database schema

**Frontend:**
- `frontend/src/app/settings/page.tsx` - Settings UI
- `frontend/src/hooks/useOutlookIntegration.ts` - OAuth flow logic
- `frontend/src/hooks/useAuth.ts` - Supabase auth

## References

- Original implementation: `c.os.4.1/server/routes/emailRoutes.ts`
- Original frontend: `c.os.4.1/client/services/outlookService.ts`
- Microsoft OAuth docs: https://learn.microsoft.com/en-us/graph/auth-v2-user
