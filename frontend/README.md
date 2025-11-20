# CelesteOS Frontend

Premium Next.js frontend for CelesteOS - Engineering Intelligence for Yachts.

**🚀 Deploy:** See [DEPLOYMENT.md](./DEPLOYMENT.md) for Vercel deployment guide.

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** TailwindCSS
- **UI Components:** shadcn/ui patterns (minimal)
- **Icons:** Lucide React
- **Backend:** Supabase (Postgres + pgvector + Storage)
- **Deployment:** Vercel

## Project Structure

```
/src
  /app
    /login          # Authentication page
    /search         # Primary search interface (Spotlight-inspired)
    /dashboard      # HOD overview & configuration
    layout.tsx      # Root layout
  /components
    SearchBar.tsx           # Universal search bar
    ResultCard.tsx          # Search result cards
    MicroActions.tsx        # Contextual action buttons
    SettingsModal.tsx       # Settings modal
    /DashboardWidgets       # Dashboard components
  /lib
    supabaseClient.ts       # Supabase client
    utils.ts                # Utility functions
  /styles
    globals.css             # Global styles & Tailwind
  /types
    index.d.ts              # TypeScript definitions
```

## Deployment

### Vercel (Recommended - Production Ready)

**Quick Deploy:**

1. Push code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Import repository → Select `frontend` directory
4. Add environment variables (see [DEPLOYMENT.md](./DEPLOYMENT.md))
5. Deploy

**Environment Variables Required:**

```env
NEXT_PUBLIC_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
NEXT_PUBLIC_API_BASE_URL=https://api.celeste7.ai/webhook/
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete instructions.

### Local Development (Optional)

```bash
npm install
cp .env.example .env.local
# Add credentials to .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Key Features

### Search Page (`/search`)
- Spotlight-inspired centered search interface
- Live streaming results
- Entity extraction & intent detection
- Contextual micro-actions
- Card-based result display

### Dashboard Page (`/dashboard`)
- HOD-only configuration & oversight
- Predictive maintenance overview
- Work order status
- Equipment overview
- Inventory tracking
- Settings & user management

### Design Philosophy
- **Zero clutter** - Minimal, focused UI
- **Streaming-first** - Progressive result loading
- **Contextual actions** - Smart micro-actions based on intent
- **Dark/light themes** - System preference support
- **Apple-inspired** - Clean typography, smooth animations

## API Integration

Endpoints configured:

- **Search:** `POST https://api.celeste7.ai/webhook/search`
- **Auth:** Supabase authentication
- **Data:** Supabase Postgres + pgvector

All endpoints are type-safe with full TypeScript definitions.

## Performance

Expected metrics on Vercel:
- **First Load:** < 1s
- **Search Response:** < 500ms
- **Lighthouse Score:** 90+

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari 14+

## License

Proprietary - Not for public distribution
