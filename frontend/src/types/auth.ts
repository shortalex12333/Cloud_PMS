export type UserRole =
  | 'chief_engineer'
  | 'eto'
  | 'captain'
  | 'manager'
  | 'hod'
  | 'crew'
  | 'vendor'

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  yacht_id: string
  yacht_name?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AuthState {
  user: User | null
  loading: boolean
  error: string | null
}
