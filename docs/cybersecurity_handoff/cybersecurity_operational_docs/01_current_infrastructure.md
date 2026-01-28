# Current Infrastructure Overview

## Control Plane (MASTER)
- Supabase project
- Owns authentication (auth.users)
- Owns memberships (user -> yacht)
- Owns fleet registry and routing metadata
- Issues JWTs

## Data Plane (TENANT)
- Supabase project(s)
- Stores yacht-specific PMS data
- Enforces isolation via yacht_id + RLS
- Mirrors user identities via profiles/roles tables

## Backend
- Action Router on Render
- Server-side Supabase clients only
- Centralised validation and intent execution

## Devices
- DMG agents enrolled via secure tokens
- Device-bound credentials and scopes
