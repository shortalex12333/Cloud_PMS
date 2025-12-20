# App Search Programming Guide (Apple Documentation Archive)

Source:
- https://developer.apple.com/library/archive/documentation/General/Conceptual/AppSearch/index.html

## What it’s useful for
This is Apple’s “big picture” explanation of **how app content gets into search** (Spotlight/Safari/Handoff/Siri Suggestions) and the concepts behind indexing and ranking.

## High-value concepts
### Two indexes (privacy model)
Apple describes a **private on-device index** and a **server-side index** (for public web content). You decide what goes where.

### “Search is several technologies”
The guide frames “search” as a combination of:
- `NSUserActivity` (activities/navigation points)
- Core Spotlight (app-specific content, persistent items)
- Web markup (public content discoverability)

### Ranking levers
The guide emphasizes relevance and ranking being tied to:
- user engagement with content
- what gets indexed (don’t index junk)
- keeping indexes current (update/remove)

Short quote (for context):
> “Privacy is a fundamental feature of search in iOS.” (Apple Documentation Archive)

## Actionable takeaways for your clone
Even if you’re not on Apple platforms, you can copy the *model*:
- Separate private/local results vs “web” results
- Use metadata-rich items (title, subtitle, kind, icon, actions)
- Keep the index fresh and prune aggressively
- Treat engagement as a ranking signal

---
