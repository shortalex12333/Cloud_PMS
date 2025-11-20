export type UserRole =
  | 'captain'          // Full yacht access
  | 'chief_engineer'   // HOD - Dashboard access
  | 'hod'              // Head of Department - Dashboard access
  | 'manager'          // Fleet manager - Dashboard access
  | 'eto'              // Electronics officer
  | 'engineer'         // Engineering crew
  | 'deck'             // Deck crew
  | 'interior'         // Interior crew
  | 'vendor'           // External service provider
  | 'readonly'         // View-only access

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  yacht_id: string
  yacht_name?: string
  is_active: boolean
  permissions?: Record<string, any>  // Custom permissions override (JSONB)
  last_login_at?: string
  created_at: string
  updated_at: string
}

export interface AuthState {
  user: User | null
  loading: boolean
  error: string | null
}
