# CelesteOS Technology Stack

## Overview
CelesteOS is a cloud-first, AI-powered Yacht Property Management System built with a modern full-stack architecture. The system is deployed across multiple cloud services with strict multi-tenancy isolation.

---

## Frontend Stack

### Languages & Runtime
- **TypeScript** - Primary language for type-safe development
- **Node.js** - Runtime environment (v18+)

### Framework & Key Dependencies
- **Next.js** ^14.2.0 - React-based framework with SSR/ISR capabilities
- **React** ^18.3.0 - UI library
- **React DOM** ^18.3.0 - DOM renderer

### UI & Components
- **Radix UI** - Accessible component library
  - `@radix-ui/react-alert-dialog` ^1.0.5
  - `@radix-ui/react-dialog` ^1.0.5
  - `@radix-ui/react-dropdown-menu` ^2.1.16
  - `@radix-ui/react-label` ^2.0.2
  - `@radix-ui/react-select` ^2.0.0
  - `@radix-ui/react-slot` ^1.0.2
- **Tailwind CSS** ^3.4.0 - Utility-first CSS framework
- **PostCSS** ^8.4.0 - CSS transformation tool
- **Lucide React** ^0.344.0 - Icon library
- **class-variance-authority** ^0.7.0 - CSS class composition utility
- **tailwind-merge** ^2.2.0 - Intelligent Tailwind CSS class merger

### Form & Validation
- **React Hook Form** ^7.66.1 - Performant form library
- **@hookform/resolvers** ^5.2.2 - Validation resolver integration
- **Zod** ^4.1.12 - TypeScript-first schema validation

### API & Data Management
- **@supabase/supabase-js** ^2.39.0 - Supabase client library
- **@tanstack/react-query** ^5.90.10 - Server state management
- **@tanstack/react-query-devtools** ^5.90.2 - Development tools for React Query

### Utilities
- **sonner** ^2.0.7 - Toast notification library
- **clsx** ^2.1.0 - Conditional className utility
- **isomorphic-dompurify** ^2.35.0 - XSS protection (DOMPurify for SSR)

### Development & Testing
- **TypeScript** ^5.3.0 - Type checker
- **Vitest** ^4.0.17 - Unit testing framework
- **@vitest/coverage-v8** ^4.0.17 - Code coverage
- **@testing-library/react** ^16.3.1 - React testing utilities
- **@testing-library/jest-dom** ^6.9.1 - DOM matchers
- **jsdom** ^27.4.0 - DOM implementation for Node.js
- **Playwright** ^1.57.0 - E2E testing framework
- **ESLint** ^8.56.0 - Code linting
- **eslint-config-next** ^14.2.0 - Next.js ESLint config

### Build Tools
- **@vitejs/plugin-react** ^5.1.2 - Vite React plugin
- **@types/node** ^20.11.0 - Node.js type definitions
- **@types/react** ^18.2.0 - React type definitions
- **@types/react-dom** ^18.2.0 - React DOM type definitions

---

## Backend Stack

### Languages & Runtime
- **Python** ^3.9+ - Primary language
- **FastAPI** 0.115.0 - Modern async web framework
- **Uvicorn** [standard] 0.32.1 - ASGI server

### Core Dependencies
- **Pydantic** 2.10.3 - Data validation and serialization
- **python-multipart** 0.0.9 - File upload support for FastAPI
- **slowapi** 0.1.9 - Rate limiting library

### Database & ORM
- **Supabase** 2.12.0 - Cloud database integration
- **psycopg2-binary** 2.9.10 - PostgreSQL adapter for direct access
- **asyncpg** >=0.27.0 - Async PostgreSQL driver
- **redis** >=4.5.0 - Cache and session storage

### Authentication & Security
- **PyJWT** 2.10.1 - JWT token handling
- **cryptography** 44.0.0 - Cryptographic algorithms
- **pydantic** 2.10.3 - Request validation and security schemas

### HTTP & API Integration
- **httpx** 0.28.1 - Async HTTP client
- **requests** 2.32.3 - Synchronous HTTP client

### Data Processing
- **jsonschema** 4.23.0 - JSON Schema validation
- **pyyaml** >=6.0 - YAML parsing
- **python-dotenv** 1.0.0 - Environment variable management
- **cachetools** 5.3.2 - In-memory TTL cache for tenant lookups

### AI & NLP
- **OpenAI** 1.59.5 - GPT-4o/GPT-4o-mini API client
- **sentence-transformers** - Removed (replaced with OpenAI embeddings)

### Development & Testing
- **pytest** 7.4.4 - Testing framework
- **pytest-asyncio** 0.23.3 - Async test support
- **pytest-cov** 4.1.0 - Code coverage
- **black** 24.1.1 - Code formatter
- **flake8** 7.0.0 - Linter
- **mypy** 1.8.0 - Static type checker

---

## Workers & Background Jobs

### Technologies
- **Python** - Same as backend
- **FastAPI** - Event handlers
- **Uvicorn** - Worker runtime
- **AsyncIO** - Async task processing
- **Redis** - Job queue and caching
- **OpenAI** >=1.0.0 - AI model inference

### Key Dependencies (workers/requirements.txt)
- **psycopg2-binary** >=2.9.0
- **openai** >=1.0.0
- **pyyaml** >=6.0

### Microservices
- **Email Watcher Worker** - Syncs Outlook/Microsoft Graph emails
- **Link Suggester Worker** - AI-powered document linking
- **Projection Worker** - Denormalization for query performance
- **Linking Requeue Worker** - Retry logic for failed linking operations

---

## Infrastructure & Deployment

### Cloud Platforms
- **Supabase** - Primary database (PostgreSQL), authentication, storage
- **Render** - Backend API deployment, Worker processes
- **Vercel** - Frontend deployment
- **Microsoft Azure** - OAuth integration for Outlook
- **OpenAI API** - GPT-4o/GPT-4o-mini models
- **Microsoft Graph API** - Email synchronization (Outlook)

### Containers
- **Docker** - Production containerization
  - `Dockerfile` - Main API
  - `Dockerfile.microaction` - Micro-action service
  - `Dockerfile.test` - Test environment
  - `Dockerfile.worker` - Background worker processes

### Environment Configuration
- `.env` files for environment-specific settings
- Environment variables pattern:
  - **Master Database**: `MASTER_SUPABASE_URL`, `MASTER_SUPABASE_SERVICE_KEY`, `MASTER_SUPABASE_JWT_SECRET`
  - **Tenant Databases**: `TENANT_1_SUPABASE_URL`, `TENANT_1_SUPABASE_SERVICE_KEY`, `TENANT_SUPABASE_JWT_SECRET`
  - **Yacht-specific**: `y{YACHT_ID}_SUPABASE_URL`, `y{YACHT_ID}_SUPABASE_SERVICE_KEY`
  - **OpenAI**: `OPENAI_API_KEY`, `AI_MODEL` (default: gpt-4o-mini)
  - **Azure OAuth**: `AZURE_READ_APP_ID`, `AZURE_READ_CLIENT_SECRET`, `AZURE_WRITE_APP_ID`, `AZURE_WRITE_CLIENT_SECRET`
  - **n8n Integration**: `N8N_BASE_URL`, `N8N_AUTH_TOKEN`
  - **API**: `ALLOWED_ORIGINS` (CORS), `ENVIRONMENT` (development/production)
  - **Feature Flags**: `FAULT_LENS_V1_ENABLED`, `EMAIL_TRANSPORT_ENABLED`

---

## Key Architectural Patterns

### Multi-Tenancy
- Master database for authentication and tenant routing
- Per-yacht tenant databases in Supabase
- Dynamic Supabase client initialization based on yacht_id

### Action Router (Micro-Action Framework)
- Centralized action registry (`action_router/registry.py`)
- Handler types: INTERNAL (Python), deprecated N8N
- Field classification system: REQUIRED, OPTIONAL, BACKEND_AUTO, CONTEXT
- Action variants: READ (read-only), MUTATE (standard), SIGNED (signature required)
- Role-based access control with gating

### Email Integration Architecture
- Read/Write token separation for Outlook OAuth
- Delta query sync for incremental inbox/sent updates
- No email body storage (metadata only)
- TTL cache (60s) for message content
- Rate limiting for Microsoft Graph API
- "Open in Outlook" web link storage

### Extraction Pipeline
- Multi-stage entity extraction with regex baseline
- AI extraction using OpenAI GPT-4o-mini (fallback graceful degradation)
- Coverage controller for extraction quality
- Entity merger for consolidated results
- Extraction triggers via document upload and email body preview

### State Management
- Row-Level Security (RLS) for database isolation
- JWT-based authentication with tenant routing
- In-memory TTL cache for tenant configuration
- Service role tokens for backend operations

---

## Testing Infrastructure

### Frontend Testing
- **Unit Tests**: Vitest with React Testing Library
- **E2E Tests**: Playwright with contract tests
- Coverage targets tracked in CI pipeline

### Backend Testing
- **Unit Tests**: Pytest with async support
- **Integration Tests**: Docker-based RLS verification
- **E2E Tests**: E2E sandbox runner for full workflows
- **Contract Tests**: JWT token format verification

---

## Version Management
- Frontend: 1.0.0
- Backend: 1.0.0
- Node.js: v18+
- Python: 3.9+
- Next.js: 14.2.0
- FastAPI: 0.115.0
- React: 18.3.0
