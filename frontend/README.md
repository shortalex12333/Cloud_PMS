# CelesteOS Frontend

Cloud-first AI-powered engineering intelligence platform for superyachts - Web Frontend

## 🚀 Tech Stack

- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui
- **Authentication:** Supabase Auth
- **API Client:** Custom typed fetch wrapper
- **Icons:** Lucide React

## 📁 Project Structure

```
frontend/
├── src/
│   ├── app/                      # Next.js App Router pages
│   │   ├── dashboard/            # HOD-only dashboard
│   │   ├── search/               # Primary search interface
│   │   ├── layout.tsx            # Root layout with AuthProvider
│   │   ├── page.tsx              # Home (redirects to /search)
│   │   └── globals.css           # Global styles
│   │
│   ├── components/               # React components
│   │   ├── ui/                   # shadcn/ui base components
│   │   │   ├── card.tsx
│   │   │   ├── button.tsx
│   │   │   └── badge.tsx
│   │   ├── widgets/              # Dashboard widgets
│   │   │   ├── RiskOverviewWidget.tsx
│   │   │   ├── WorkOrdersWidget.tsx
│   │   │   ├── InventoryWidget.tsx
│   │   │   ├── FaultsWidget.tsx
│   │   │   ├── UpcomingTasksWidget.tsx
│   │   │   └── FleetWidget.tsx
│   │   └── DashboardLayout.tsx   # Dashboard page layout
│   │
│   ├── contexts/                 # React contexts
│   │   └── AuthContext.tsx       # Authentication state
│   │
│   ├── lib/                      # Utility functions
│   │   ├── api.ts                # Typed API client
│   │   ├── supabase.ts           # Supabase client
│   │   ├── mockData.ts           # Mock data for development
│   │   └── utils.ts              # Utility functions (cn)
│   │
│   └── types/                    # TypeScript type definitions
│       ├── api.ts                # API types
│       ├── auth.ts               # Auth types
│       └── dashboard.ts          # Dashboard types
│
├── public/                       # Static assets
├── .env.example                  # Environment variables template
├── next.config.js                # Next.js configuration
├── tailwind.config.ts            # Tailwind configuration
├── tsconfig.json                 # TypeScript configuration
└── package.json                  # Dependencies
```

## 🛠 Setup Instructions

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# API Configuration (n8n Cloud Webhook Base URL)
NEXT_PUBLIC_API_BASE_URL=https://api.celeste7.ai/webhook
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📖 Key Features

### Two-Page UX Model

CelesteOS follows a minimalist two-page design:

1. **`/search`** - Primary interface (95% of user time)
   - Universal search bar
   - Dynamic result cards
   - Context-aware micro-actions
   - Used by all crew members

2. **`/dashboard`** - HOD-only control room
   - Risk overview
   - Work orders status
   - Inventory alerts
   - Faults summary
   - Upcoming tasks
   - Fleet comparison (optional)

### Dashboard Widgets

All widgets are **read-only** and follow these rules:

- ✅ Show where attention is needed
- ✅ Provide quick visibility
- ✅ Navigate to search for actions
- ❌ No create/edit buttons on dashboard
- ❌ No direct data mutation

Clicking any item navigates to `/search` with a pre-filled query.

### Authentication & Access Control

- **Supabase Auth** with JWT tokens
- **Role-based access control**:
  - `chief_engineer`, `hod`, `manager`, `captain` → Can access dashboard
  - `crew`, `eto`, `vendor` → Search only
- Automatic redirect if unauthorized

## 🎨 Design System

### Colors

- Uses Tailwind CSS with shadcn/ui theme
- Minimal, desaturated palette
- Color only for state:
  - Red: Critical, overdue, high risk
  - Orange: Warning, medium risk
  - Yellow: Attention needed
  - Green: Normal, good
  - Blue: Informational

### Typography

- Font: Inter (via Google Fonts)
- Clean, readable hierarchy
- Minimal use of bold/emphasis

### Components

Built with shadcn/ui for consistency:

- `Card` - Container for widgets
- `Button` - Actions and navigation
- `Badge` - Status indicators
- All components are unstyled by default, styled with Tailwind

## 🔌 API Integration

### Current Status

Dashboard uses **mock data** (`src/lib/mockData.ts`) for development.

When backend is ready, replace in `src/app/dashboard/page.tsx`:

```typescript
// Replace this:
setRiskData(mockRiskOverviewData)

// With this:
const risk = await api.predictive.getInsights()
setRiskData(risk.insights)
```

### API Client

Typed API client in `src/lib/api.ts`:

```typescript
import { api } from '@/lib/api'

// Search
const results = await api.search.search({ query: 'fault E047' })

// Dashboard
const summary = await api.dashboard.getSummary()
const workOrders = await api.dashboard.getWorkOrders()

// Predictive
const insights = await api.predictive.getInsights()
```

## 🧪 Testing

```bash
# Type checking
npm run type-check

# Linting
npm run lint

# Build
npm run build
```

## 📦 Build & Deploy

### Production Build

```bash
npm run build
npm start
```

### Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Production deployment
vercel --prod
```

### Environment Variables

Ensure these are set in your deployment platform:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_BASE_URL`

## 🔒 Security

- All API requests include JWT token
- Row-level security enforced by Supabase
- Yacht-based data isolation
- No PII stored in frontend
- Presigned URLs for document access

## 📚 Documentation References

- [web-ux.md](../web-ux.md) - UX specification
- [dashboard-spec.md](../dashboard-spec.md) - Dashboard requirements
- [api-spec.md](../api-spec.md) - API endpoints
- [security.md](../security.md) - Security architecture

## 🤝 Development Workflow

1. **Tasks 1-7**: Foundation setup ✅ COMPLETE
   - Next.js, TypeScript, Tailwind, shadcn/ui
   - Auth context, API client, types
   - Search page skeleton, dashboard skeleton

2. **Task 8**: Dashboard implementation ✅ COMPLETE
   - All 6 widgets implemented
   - Grid layout with responsive design
   - Mock data integration
   - Navigation to search

3. **Next Steps**:
   - Wire up real API endpoints
   - Implement search functionality
   - Add loading states & error handling
   - Write unit tests
   - Add more widgets as needed

## 👥 Team

**Worker 8** - Dashboard Orchestrator (Frontend Logic)
- Role: Dashboard page & widgets
- Skills: Next.js server components, card layouts, grid UX
- Constraints: No backend mutation from dashboard

## 🆘 Support

For issues or questions, see the main project documentation or contact the engineering team.

---

**Last Updated**: 2025-11-20
**Version**: 1.0.0
**Status**: Tasks 1-8 Complete, Ready for backend integration
