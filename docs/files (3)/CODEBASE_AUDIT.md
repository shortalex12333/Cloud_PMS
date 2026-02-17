# CODEBASE AUDIT — Run Before FE-Phase 0

> This audit MUST complete before any design system work begins.
> Hardcoded styles, duplicate files, and legacy CSS will silently override your new tokens.
> Find them. Log them. Fix them. Then build.

---

## AUDIT 1: Hardcoded Colors

### What to scan for

```bash
# Find ALL hardcoded hex colors in source files
grep -rn --include="*.tsx" --include="*.ts" --include="*.css" --include="*.scss" --include="*.jsx" --include="*.js" '#[0-9a-fA-F]\{3,8\}' src/ | grep -v node_modules | grep -v '.test.' > audit_hardcoded_colors.txt

# Find ALL rgb/rgba inline values
grep -rn --include="*.tsx" --include="*.ts" --include="*.css" --include="*.jsx" 'rgb\(|rgba\(' src/ | grep -v node_modules >> audit_hardcoded_colors.txt

# Find ALL hsl/hsla inline values
grep -rn --include="*.tsx" --include="*.ts" --include="*.css" --include="*.jsx" 'hsl\(|hsla\(' src/ | grep -v node_modules >> audit_hardcoded_colors.txt

# Count total hardcoded color instances
echo "=== TOTAL HARDCODED COLORS ===" >> audit_hardcoded_colors.txt
wc -l audit_hardcoded_colors.txt >> audit_hardcoded_colors.txt
```

### What to do with results

For EVERY hardcoded color found:
1. Identify which semantic token it maps to (check CLAUDE.md token definitions)
2. If it maps to an existing token → replace with `var(--token-name)` or Tailwind class
3. If it doesn't map → decide: is this a missing token we need to add, or dead code?
4. Log the replacement in PROGRESS_LOG.md: `[file:line] #1A1A1A → var(--surface-elevated)`

### Common offenders to watch for

| Hardcoded pattern | Likely replacement |
|---|---|
| `#000`, `#000000`, `black` | `var(--surface-base)` or `var(--text-primary)` depending on context |
| `#fff`, `#ffffff`, `white` | `var(--text-primary)` in dark mode context, `var(--surface-base)` in light |
| `#1a1a1a`, `#1e1e1e`, `#171717`, `#141414` | `var(--surface-primary)` or `var(--surface-elevated)` |
| `#333`, `#444`, `#555`, `#666` | `var(--text-tertiary)` or `var(--surface-border)` |
| `#999`, `#aaa`, `#bbb` | `var(--text-secondary)` |
| `#e5e5e5`, `#eee`, `#f0f0f0` | `var(--surface-border)` (light mode) |
| Any teal/blue: `#3A7C9D`, `#2faadf`, `#badde9`, `#2B8FB3` | `var(--brand-ambient)` or `var(--brand-interactive)` |
| Any red: `#ff0000`, `#e5484d`, `#dc3545` | `var(--status-critical)` |
| Any green: `#00ff00`, `#30a46c`, `#28a745` | `var(--status-success)` |
| Any amber/yellow: `#f5a623`, `#ffc107` | `var(--status-warning)` |

---

## AUDIT 2: Inline Styles

### What to scan for

```bash
# Find ALL inline style attributes in JSX/TSX
grep -rn --include="*.tsx" --include="*.jsx" 'style={{' src/ | grep -v node_modules > audit_inline_styles.txt
grep -rn --include="*.tsx" --include="*.jsx" 'style={' src/ | grep -v node_modules >> audit_inline_styles.txt

# Find CSS-in-JS patterns (styled-components, emotion, etc.)
grep -rn --include="*.tsx" --include="*.ts" 'styled\.' src/ | grep -v node_modules >> audit_inline_styles.txt
grep -rn --include="*.tsx" --include="*.ts" 'css`' src/ | grep -v node_modules >> audit_inline_styles.txt

# Count
echo "=== TOTAL INLINE STYLES ===" >> audit_inline_styles.txt
wc -l audit_inline_styles.txt >> audit_inline_styles.txt
```

### What to do with results

Inline styles OVERRIDE CSS custom properties and Tailwind classes. They are the #1 reason new tokens "don't work."

For every inline style found:
1. If it sets color/background/border → MUST be converted to token or Tailwind class
2. If it sets layout (width, height, position) → acceptable in rare cases (dynamic values), but prefer Tailwind
3. If it sets font-size/font-weight → MUST use type scale from UI_SPEC.md
4. If it sets padding/margin → MUST use spacing scale (4px increments)
5. If it sets border-radius → MUST use radius tokens
6. If it sets box-shadow → MUST use shadow tokens

**Priority: eliminate ALL inline color/background/border styles first. These directly prevent token adoption.**

---

## AUDIT 3: Competing CSS Files

### What to scan for

```bash
# Find ALL CSS/SCSS files in the project
find src/ -name "*.css" -o -name "*.scss" -o -name "*.module.css" -o -name "*.module.scss" | grep -v node_modules | sort > audit_css_files.txt

# Find global CSS imports (these can override everything)
grep -rn --include="*.tsx" --include="*.ts" --include="*.jsx" --include="*.js" "import.*\.css" src/ | grep -v node_modules | grep -v '.module.' > audit_global_css_imports.txt

# Find Tailwind @apply directives that might hardcode values
grep -rn '@apply' src/ | grep -v node_modules > audit_tailwind_apply.txt

# Find !important overrides
grep -rn '!important' src/ | grep -v node_modules > audit_important_overrides.txt

# Count all
echo "=== CSS FILES ===" && wc -l audit_css_files.txt
echo "=== GLOBAL CSS IMPORTS ===" && wc -l audit_global_css_imports.txt
echo "=== @APPLY DIRECTIVES ===" && wc -l audit_tailwind_apply.txt
echo "=== !IMPORTANT OVERRIDES ===" && wc -l audit_important_overrides.txt
```

### CSS load order matters

The CSS that loads LAST wins. Check:
1. What order are CSS files imported in `_app.tsx` or `layout.tsx`?
2. Is `tokens.css` imported FIRST (so everything else can reference its vars)?
3. Are there global resets or normalize.css files that set colors/fonts?
4. Are there component-level CSS modules that hardcode values that override tokens?

**The fix:** `tokens.css` must be the FIRST CSS import in the app root. Everything downstream references tokens. Nothing upstream overrides them.

### !important is a red flag

Every `!important` in the codebase is a potential token override. Audit each one:
- If it's forcing a hardcoded color → remove it, use token
- If it's solving a specificity war → fix the specificity, remove !important
- If it's in a third-party library override → acceptable but document it

---

## AUDIT 4: Duplicate & Shadowed Files

### What to scan for

```bash
# Find files with identical names in different directories
find src/ -type f \( -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" \) | grep -v node_modules | xargs -I{} basename {} | sort | uniq -d > audit_duplicate_names.txt

# For each duplicate name, show all paths
while read name; do
  echo "=== $name ===" >> audit_duplicate_paths.txt
  find src/ -name "$name" -not -path "*/node_modules/*" >> audit_duplicate_paths.txt
done < audit_duplicate_names.txt

# Find components that might shadow each other (same component name, different files)
grep -rn --include="*.tsx" --include="*.jsx" "export default function\|export const\|export function" src/ | grep -v node_modules | awk -F'[ (]' '{for(i=1;i<=NF;i++) if($i ~ /^[A-Z]/) print $i, FILENAME}' | sort | uniq -d -f0 > audit_component_shadows.txt

# Find barrel exports (index.ts files) that might re-export the wrong version
find src/ -name "index.ts" -o -name "index.tsx" | grep -v node_modules | xargs grep "export" > audit_barrel_exports.txt
```

### Why duplicates are dangerous

If `StatusPill.tsx` exists in both `src/components/StatusPill.tsx` and `src/components/ui/StatusPill.tsx`:
- Import `from '@/components/StatusPill'` gets one version
- Import `from '@/components/ui/StatusPill'` gets the other
- You update one, the other stays stale
- Different parts of the app render different versions
- Your new design system component is invisible because imports point to the old one

### What to do with results

For every duplicate:
1. **Identify which is authoritative.** Check git blame — which was modified most recently?
2. **Check imports.** Which version do existing components actually import?
3. **Consolidate.** Keep ONE version in ONE location. Update all imports.
4. **Delete the duplicate.** Do not comment it out. Delete it.

For new components you create:
1. Place in a SINGLE canonical location (e.g., `src/components/ui/`)
2. Export from a barrel file (`src/components/ui/index.ts`)
3. Search the ENTIRE codebase to confirm no old version of the same component exists elsewhere
4. After creating, run: `find src/ -name "YourComponentName*" | grep -v node_modules` — if more than one result, you have a problem

---

## AUDIT 5: Tailwind Config Conflicts

### What to scan for

```bash
# Find ALL tailwind config files (there might be more than one)
find . -name "tailwind.config.*" -not -path "*/node_modules/*" > audit_tailwind_configs.txt

# Check for hardcoded theme values in tailwind config
cat tailwind.config.* | grep -A5 "colors:" > audit_tailwind_theme_colors.txt

# Check for custom utilities that might conflict
cat tailwind.config.* | grep -A5 "extend:" > audit_tailwind_extend.txt
```

### What to do

1. There should be EXACTLY ONE `tailwind.config.js` (or `.ts`). If multiple exist, consolidate.
2. Check if colors are hardcoded in the config (`colors: { primary: '#3A7C9D' }`) — these must be replaced with CSS var references as defined in CLAUDE.md.
3. Check for custom color names that conflict with the token system (e.g., if there's already a `brand` or `surface` key in the config).
4. The Tailwind config extension in CLAUDE.md adds: `brand`, `status`, `surface`, `txt`. Verify no existing keys collide.

---

## AUDIT 6: Font Loading

### What to scan for

```bash
# Find font imports
grep -rn "font-family\|@font-face\|@import.*font\|fonts.googleapis" src/ | grep -v node_modules > audit_fonts.txt

# Find Next.js font imports
grep -rn "next/font" src/ | grep -v node_modules >> audit_fonts.txt

# Find font files in project
find . -name "*.woff*" -o -name "*.ttf" -o -name "*.otf" | grep -v node_modules >> audit_fonts.txt
```

### What to do

1. If custom fonts are loaded that aren't in the system font stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif`) → evaluate if they're needed
2. If heavy web fonts load from Google Fonts → this adds latency on satellite WiFi. Consider self-hosting critical weights only (400, 500, 600) or removing in favor of system fonts
3. If Next.js `next/font` is used with Inter → good, keep it, but ensure the CSS var `--font-family` references it correctly
4. If multiple font families are declared → consolidate to ONE stack as defined in CLAUDE.md

---

## AUDIT 7: Z-Index Chaos

### What to scan for

```bash
# Find ALL z-index declarations
grep -rn 'z-index' src/ | grep -v node_modules > audit_zindex.txt

# Sort by value to see the range
grep -rn 'z-index' src/ | grep -v node_modules | grep -oP 'z-index:\s*\K[0-9]+' | sort -n | uniq -c | sort -rn > audit_zindex_values.txt
```

### What to do

The token system defines a z-index scale:
```
--z-sticky: 10    (section headers)
--z-header: 20    (lens header)
--z-sidebar: 30   (Show Related)
--z-modal: 40     (signature modals)
--z-search: 50    (search bar)
--z-toast: 60     (notifications)
```

If the codebase has z-index values like `999`, `9999`, `100`, `50` scattered randomly:
1. Map each to the closest token level
2. Replace hardcoded values with `var(--z-level)`
3. If two elements fight for the same level, one of them is architecturally wrong — fix the architecture, don't bump z-index

---

## RUNNING THE FULL AUDIT

### One-command audit script

```bash
#!/bin/bash
# Save as: audit_codebase.sh
# Run from repo root: bash audit_codebase.sh

AUDIT_DIR=".claude/audit"
mkdir -p $AUDIT_DIR

echo "🔍 Auditing hardcoded colors..."
grep -rn --include="*.tsx" --include="*.ts" --include="*.css" --include="*.scss" --include="*.jsx" '#[0-9a-fA-F]\{3,8\}' src/ 2>/dev/null | grep -v node_modules > $AUDIT_DIR/hardcoded_colors.txt
echo "  Found: $(wc -l < $AUDIT_DIR/hardcoded_colors.txt) instances"

echo "🔍 Auditing inline styles..."
grep -rn --include="*.tsx" --include="*.jsx" 'style={{' src/ 2>/dev/null | grep -v node_modules > $AUDIT_DIR/inline_styles.txt
echo "  Found: $(wc -l < $AUDIT_DIR/inline_styles.txt) instances"

echo "🔍 Auditing CSS files..."
find src/ -name "*.css" -o -name "*.scss" -o -name "*.module.css" 2>/dev/null | grep -v node_modules | sort > $AUDIT_DIR/css_files.txt
echo "  Found: $(wc -l < $AUDIT_DIR/css_files.txt) files"

echo "🔍 Auditing !important overrides..."
grep -rn '!important' src/ 2>/dev/null | grep -v node_modules > $AUDIT_DIR/important_overrides.txt
echo "  Found: $(wc -l < $AUDIT_DIR/important_overrides.txt) instances"

echo "🔍 Auditing duplicate filenames..."
find src/ -type f \( -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" \) 2>/dev/null | grep -v node_modules | xargs -I{} basename {} | sort | uniq -d > $AUDIT_DIR/duplicate_names.txt
echo "  Found: $(wc -l < $AUDIT_DIR/duplicate_names.txt) duplicated names"

echo "🔍 Auditing z-index values..."
grep -rn 'z-index' src/ 2>/dev/null | grep -v node_modules > $AUDIT_DIR/zindex.txt
echo "  Found: $(wc -l < $AUDIT_DIR/zindex.txt) instances"

echo "🔍 Auditing font declarations..."
grep -rn 'font-family\|@font-face\|@import.*font' src/ 2>/dev/null | grep -v node_modules > $AUDIT_DIR/fonts.txt
echo "  Found: $(wc -l < $AUDIT_DIR/fonts.txt) instances"

echo "🔍 Auditing global CSS imports..."
grep -rn --include="*.tsx" --include="*.ts" "import.*\.css" src/ 2>/dev/null | grep -v node_modules | grep -v '.module.' > $AUDIT_DIR/global_css_imports.txt
echo "  Found: $(wc -l < $AUDIT_DIR/global_css_imports.txt) global CSS imports"

echo ""
echo "✅ Audit complete. Results in $AUDIT_DIR/"
echo ""
echo "=== SUMMARY ==="
echo "Hardcoded colors:  $(wc -l < $AUDIT_DIR/hardcoded_colors.txt)"
echo "Inline styles:     $(wc -l < $AUDIT_DIR/inline_styles.txt)"
echo "CSS files:         $(wc -l < $AUDIT_DIR/css_files.txt)"
echo "!important:        $(wc -l < $AUDIT_DIR/important_overrides.txt)"
echo "Duplicate names:   $(wc -l < $AUDIT_DIR/duplicate_names.txt)"
echo "Z-index:           $(wc -l < $AUDIT_DIR/zindex.txt)"
echo "Font declarations: $(wc -l < $AUDIT_DIR/fonts.txt)"
echo "Global CSS:        $(wc -l < $AUDIT_DIR/global_css_imports.txt)"
```

### Audit exit criteria

The audit is DONE when:
- [ ] All audit results logged to `.claude/audit/`
- [ ] Every hardcoded color categorized: token replacement identified OR marked as dead code
- [ ] Every inline style categorized: must-convert OR acceptable-dynamic-value
- [ ] Every duplicate file identified: authoritative version chosen, delete plan ready
- [ ] CSS load order documented: tokens.css confirmed as first import
- [ ] Z-index values mapped to token scale
- [ ] Findings summarized in PROGRESS_LOG.md
- [ ] NO FIXES YET — audit is observation only. Fixes happen in FE-Phase 0.

---

## POST-AUDIT: New File Hygiene Rules

### When creating ANY new component:

```bash
# BEFORE creating: check if a version already exists
find src/ -iname "*YourComponentName*" | grep -v node_modules

# AFTER creating: verify only ONE version exists
find src/ -iname "*YourComponentName*" | grep -v node_modules
# Must return exactly 1 result
```

### Canonical component locations

```
src/
├── components/
│   ├── ui/              ← Design system primitives (StatusPill, GhostButton, Toast, etc.)
│   │   └── index.ts     ← Barrel export: export { StatusPill } from './StatusPill'
│   ├── lens/            ← Lens-specific components (WorkOrderHeader, FaultVitalSigns, etc.)
│   │   └── index.ts
│   ├── layout/          ← Layout components (LensLayout, NavigationHeader, SearchBar, etc.)
│   │   └── index.ts
│   └── shared/          ← Cross-cutting (SignatureModal, FilePreviewCard, etc.)
│       └── index.ts
```

### Import rules

- ALWAYS import from barrel: `import { StatusPill } from '@/components/ui'`
- NEVER import from the file directly: ~~`import { StatusPill } from '@/components/ui/StatusPill'`~~
- This way, if a component moves, you update ONE barrel file, not every import

### After EVERY new file creation, run:

```bash
# Verify no duplicates introduced
find src/ -type f -name "$(basename YOUR_NEW_FILE)" | grep -v node_modules | wc -l
# Must equal 1

# Verify no stale imports pointing to old locations
grep -rn "OLD_IMPORT_PATH" src/ | grep -v node_modules
# Must return 0 results
```
