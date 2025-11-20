# CelesteOS Frontend

**Version:** 1.0.0

Next.js 14 frontend for CelesteOS with protected routes and role-based access control.

## Features

- **Protected Routes**: Middleware-based route protection
- **Role-Based Access**: HOD/Engineer access to dashboard
- **Supabase Auth**: Integrated authentication
- **Search Integration**: Connects to search engine API

## Protected Routes

```typescript
/dashboard → Allowed: HOD, Engineer, Chief Engineer, ETO
/search → Allowed: All authenticated users
```

If user lacks permission, redirected to `/search`.

## Installation

```bash
cd frontend
npm install
```

## Configuration

Copy `.env.local.example` to `.env.local`:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_SEARCH_API_URL=http://localhost:8000
```

## Running

```bash
npm run dev
```

Access at: `http://localhost:3000`

## Middleware Logic

`middleware.ts` checks:

1. **Authentication**: Session exists?
2. **Role Retrieval**: Get user role from database
3. **Permission Check**: Role allowed for route?
4. **Redirect**: If not allowed → `/search`

## Project Structure

```
frontend/
├── app/              # Next.js 14 app directory
├── components/       # React components
├── lib/
│   ├── supabase.ts   # Supabase client
│   └── search-api.ts # Search API client
├── middleware.ts     # Route protection
└── package.json
```

## API Integration

### Search API

```typescript
import { search } from '@/lib/search-api'

const results = await search(
  { query: "fault code E047" },
  accessToken,
  yachtSignature
)
```

### Supabase

```typescript
import { supabase } from '@/lib/supabase'

const { data: { session } } = await supabase.auth.getSession()
```

## Deployment

```bash
npm run build
npm start
```

Or deploy to Vercel:

```bash
vercel deploy
```

## User Roles

- **HOD** (Head of Department) - Full access
- **Engineer** - Full access
- **Chief Engineer** - Full access
- **ETO** (Electrical Technical Officer) - Full access
- **Deck/Interior** - Search only

## Security

- All routes require authentication
- Role-based access enforced by middleware
- JWT tokens from Supabase
- No sensitive data in client
