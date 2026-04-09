 Email Lens — Complete Picture

  What It's For

  The email lens turns Outlook into a connected part of yacht operations. Crew don't switch between email and CelesteOS — emails flow
  into the platform automatically, become searchable alongside work orders and equipment records, and can be attached as evidence to
  any entity. Crew can also send emails directly from within CelesteOS, keeping the communication trail inside the maintenance system.

  Two Azure Apps

  ┌──────────────────────┬───────────────────────────┬──────────────────────────────────────────────────┐
  │         App          │        Permissions        │                     Purpose                      │
  ├──────────────────────┼───────────────────────────┼──────────────────────────────────────────────────┤
  │ Read app (41f6dc82)  │ Files.Read.All, User.Read │ Sync inbox, fetch message bodies, search         │
  ├──────────────────────┼───────────────────────────┼──────────────────────────────────────────────────┤
  │ Write app (f0b8944b) │ Mail.Send                 │ Send emails, create drafts from within CelesteOS │
  └──────────────────────┴───────────────────────────┴──────────────────────────────────────────────────┘

  Background Worker: email-watcher

  Runs continuously, polls every 30 seconds:

  1. Finds mailboxes due for sync — calls get_email_watchers_due_for_sync RPC
  2. Refreshes tokens proactively — checks tokens expiring within 5 minutes, refreshes them before they die
  3. Syncs new messages — uses Microsoft Graph delta queries to get only new/changed messages since last sync
  4. Stores metadata only — subject, sender, recipients, timestamps, attachments list, conversation thread ID. Does NOT store email
  bodies (privacy by design)
  5. Indexes for search — writes to search_index so emails appear in F1 search results alongside work orders, equipment, etc.
  6. Tracks threads — groups messages into conversation threads in email_threads table

  User-Facing Capabilities

  ┌──────────────────────┬──────────────────────────────────────────────────────────────────────────┬─────────────────────────────┐
  │      Capability      │                               How It Works                               │           Status            │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Browse inbox         │ GET /email/inbox — lists threads sorted by last activity, shows subject, │ ✅ Working                  │
  │                      │  message count, read/unread, attachments                                 │                             │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ View thread          │ GET /email/thread/{id} — shows all messages in a conversation with       │ ✅ Working                  │
  │                      │ metadata                                                                 │                             │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Read message body    │ GET /email/message/{id}/render — fetches full HTML body live from        │ ✅ Working (token           │
  │                      │ Microsoft Graph (not stored, fetched on demand)                          │ refreshed)                  │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Mark as read         │ POST /email/thread/{id}/mark-read — sets is_read=true on thread          │ ✅ Built                    │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Search emails        │ GET /email/search — semantic search across synced email subjects and     │ ✅ Working                  │
  │                      │ metadata                                                                 │                             │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Search entities to   │ GET /email/search-objects — find work orders, equipment, faults etc. to  │ ✅ Working                  │
  │ link                 │ link an email to                                                         │                             │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Link email to entity │ POST /email/link/create — attach an email thread as evidence to a work   │ ✅ Built                    │
  │                      │ order, fault, equipment record, etc.                                     │                             │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Accept/reject link   │ POST /email/link/accept, /reject — approve or reject a proposed link     │ ✅ Built                    │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ View linked emails   │ GET /email/related — open a work order, see all emails linked to it      │ ✅ Working                  │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ View thread links    │ GET /email/thread/{id}/links — see what entities an email is linked to   │ ✅ Working                  │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Save attachment as   │ POST /email/evidence/save-attachment — save an email attachment into the │ ✅ Built                    │
  │ document             │  yacht's document library                                                │                             │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Send email           │ GraphWriteClient.send_message() — compose and send from within CelesteOS │ ✅ Code built, ❌ no write  │
  │                      │  via the write app                                                       │ token provisioned           │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Create draft         │ GraphWriteClient.create_draft() — save a draft in Outlook                │ ✅ Code built, ❌ no write  │
  │                      │                                                                          │ token provisioned           │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Force sync           │ POST /email/sync/now — trigger immediate sync instead of waiting for     │ ✅ Built                    │
  │                      │ next poll                                                                │                             │
  ├──────────────────────┼──────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ Worker status        │ GET /email/worker/status — check if email connection is active           │ ✅ Working                  │
  └──────────────────────┴──────────────────────────────────────────────────────────────────────────┴─────────────────────────────┘

  Available Actions (from entity lens)

  When viewing an email thread, these actions appear:

  The email doesn't go through the standard available_actions system like other lenses — it has its own dedicated routes for linking,
  marking read, saving attachments, etc. The actions are built into the email UI directly rather than via the registry.

  Data Flow

  Outlook Inbox
      ↓ (every 30s, email-watcher polls via Graph delta API)
  email_messages table (metadata only: subject, sender, timestamps)
  email_threads table (grouped conversations)
  search_index (indexed for F1 search)
      ↓
  User opens email lens
      ↓
  Inbox shows threads (from DB — fast)
  User clicks a thread → messages listed (from DB — fast)
  User clicks a message → body fetched LIVE from Microsoft Graph (not stored)
  User links email to work order → email_entity_links table
  User opens work order → sees linked emails in related panel

  What's Not Working Right Now

  ┌─────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │      Item       │                                                     Why                                                     │
  ├─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Message body    │ Token was expired (now refreshed ✅), but all test emails were deleted from Outlook inbox. Need new emails  │
  │ render          │ to test.                                                                                                    │
  ├─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Send/compose    │ Write app token (f0b8944b) not provisioned. User needs to OAuth with the write app.                         │
  ├─────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Email watcher   │ No email watcher configured for PMS yacht. The email_watchers table has a row with user a35cad0b but the    │
  │ sync            │ worker reports "disconnected" — need to verify the watcher is enabled and not paused.                       │
  └─────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Token Architecture

  User authenticates once with Read app → read token stored
  User authenticates once with Write app → write token stored
                                            ↓
  email-watcher uses read token to sync inbox (background, every 30s)
  render endpoint uses read token to fetch body (on demand, per click)
  send endpoint uses write token to send (on demand, per compose)
                                            ↓
  Proactive refresh heartbeat keeps both tokens alive
  (checks every 60s, refreshes tokens expiring within 5 min)
