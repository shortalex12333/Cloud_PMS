# CelesteOS Frontend

Premium, minimal, streaming-first interface for CelesteOS - Engineering Intelligence for Yachts.

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

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Add your Supabase credentials to .env.local
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Build

```bash
npm run build
npm start
```

## Environment Variables

Create a `.env.local` file with:

```env
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

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

The frontend is prepared for streaming API integration:

- `POST /api/search` - Main search endpoint (placeholder)
- Supabase client configured for auth & data
- Type-safe with full TypeScript definitions

## Deployment

### Vercel (Recommended)

```bash
vercel
```

Configure environment variables in Vercel dashboard.

## TODO

- [ ] Connect Supabase authentication
- [ ] Implement actual search API calls
- [ ] Add streaming response handling
- [ ] Connect dashboard to real data
- [ ] Implement yacht signature validation
- [ ] Add mobile photo upload
- [ ] Create handover export functionality

## License

Proprietary - Not for public distribution
