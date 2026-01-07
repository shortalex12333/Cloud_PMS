# 🚀 CelesteOS Multi-Worker Development Workflow

**Version:** 1.0
**Last Updated:** 2025-11-20

---

## 🎯 **Overview**

This repository uses a **parallel multi-worker development model** with strict branching rules to prevent merge conflicts and maintain code quality across 9 simultaneous AI workers.

---

## 🌳 **Branch Structure**

### **Main Branches**

```
main     → Stable production-ready code (protected)
develop  → Integration branch for worker PRs (protected)
```

### **Worker Branches**

Each worker must use this naming pattern:

```
claude/worker-<id>-<subsystem>-<session-id>
```

**Examples:**

```
claude/worker-2-frontend-01TwqiaKXUk14frUXUPkVKTj
claude/worker-4-local-agent-02AbcDefGhIjKlMn
claude/worker-6-search-engine-03XyZaBcDeFgHiJk
```

**Why this format?**
- `claude/` prefix → Required for push authentication
- `worker-<id>-<subsystem>` → Clear ownership and scope
- `<session-id>` → Required for push authorization

---

## 👥 **Worker Assignments**

| Worker | Subsystem | Folder Ownership |
|--------|-----------|------------------|
| Worker 1 | Database Engineer | `/database`, `/supabase` |
| Worker 2 | Frontend Engineer | `/frontend` |
| Worker 3 | Backend API Engineer | `/backend-api` |
| Worker 4 | Local Agent Engineer | `/local-agent` |
| Worker 5 | Cloud Ingestion Engineer | `/cloud-ingest`, `/n8n-workflows` |
| Worker 6 | Search Engine Engineer | `/search-engine` |
| Worker 7 | Predictive Maintenance Engineer | `/predictive` |
| Worker 8 | Mobile Engineer | `/mobile` |
| Worker 9 | Integration Engineer | `/integrations` |

**Rules:**
- ✅ Workers can freely modify their own folders
- ⚠️ Cross-folder changes require PR + review request
- ❌ Never push directly to `main` or `develop`

---

## 📝 **Pull Request Workflow**

### **1. Create PR**

**Title Format:**
```
[Worker #] <Task Name> — <Short Summary>
```

**Examples:**
```
[Worker 2] Frontend Foundation — Next.js scaffold + Tailwind + auth
[Worker 4] MVP Agent — Basic file upload and SHA256 verification
[Worker 6] Search Core — Entity extraction module
```

### **2. PR Requirements**

✅ **Must include:**
- Clear description of changes
- Only modifications to owned subsystem
- Updated documentation (if applicable)
- Type-safe TypeScript (for TS files)

❌ **Must NOT include:**
- Changes to other workers' folders
- Direct commits to `main` or `develop`
- Merge conflicts

### **3. PR Target**

**All PRs merge to:** `develop` (NOT `main`)

```
worker branch → develop → main
```

### **4. Review Process**

1. Worker creates PR to `develop`
2. Lead engineer reviews
3. After approval → merge to `develop`
4. After integration cycle → `develop` → `main`

---

## 🔒 **Branch Protection Rules**

### **For `main`:**
- ❌ No direct pushes
- ✅ Requires PR
- ✅ Requires review approval
- ✅ Must pass CI checks

### **For `develop`:**
- ❌ No direct pushes
- ✅ Requires PR from worker branches
- ✅ Workers cannot self-merge
- ✅ Must pass CI checks

### **For worker branches:**
- ✅ Worker has full control
- ✅ Can force-push if needed
- ⚠️ Must follow naming convention

---

## 🛠️ **Development Process**

### **Starting New Work**

```bash
# Fetch latest
git fetch origin

# Create worker branch (example for Worker 2)
git checkout -b claude/worker-2-<task>-<session-id>

# Start coding...
```

### **Committing Changes**

```bash
git add <files>
git commit -m "Clear, descriptive message"
git push -u origin claude/worker-2-<task>-<session-id>
```

### **Creating PR**

```bash
# Via GitHub CLI
gh pr create --base develop --title "[Worker 2] Task Name — Summary"

# Or use GitHub web interface
```

---

## 📊 **CI/CD Pipeline**

### **Automated Checks**

All PRs must pass:
- ✅ TypeScript type checking
- ✅ ESLint (no errors)
- ✅ Build test (`npm run build`)
- ✅ No merge conflicts

### **Optional Checks**
- Unit tests (when available)
- E2E tests (when available)

---

## 🚨 **Conflict Resolution**

If you encounter conflicts:

1. **Fetch latest `develop`:**
   ```bash
   git fetch origin develop
   ```

2. **Rebase your branch:**
   ```bash
   git rebase origin/develop
   ```

3. **Resolve conflicts manually**

4. **Force push:**
   ```bash
   git push --force-with-lease
   ```

---

## 📁 **Folder Structure**

```
/Cloud_PMS
├── /frontend              # Worker 2
├── /backend-api           # Worker 3
├── /database              # Worker 1
├── /local-agent           # Worker 4
├── /search-engine         # Worker 6
├── /predictive            # Worker 7
├── /cloud-ingest          # Worker 5
├── /n8n-workflows         # Worker 5
├── /mobile                # Worker 8
├── /integrations          # Worker 9
├── /docs                  # Shared (all workers)
├── /scripts               # Shared utilities
└── WORKFLOW.md            # This file
```

---

## ✅ **Best Practices**

### **DO:**
- ✅ Commit frequently with clear messages
- ✅ Keep PRs focused on single features
- ✅ Update docs when changing APIs
- ✅ Test locally before pushing
- ✅ Ask for cross-worker reviews when needed

### **DON'T:**
- ❌ Push to `main` directly
- ❌ Modify other workers' folders without PR
- ❌ Create merge commits (use rebase)
- ❌ Leave commented-out code
- ❌ Commit secrets or credentials

---

## 🔗 **Quick Links**

- **Create PR:** [GitHub PR Interface](https://github.com/shortalex12333/Cloud_PMS/pulls)
- **CI Status:** [GitHub Actions](https://github.com/shortalex12333/Cloud_PMS/actions)
- **Issues:** [GitHub Issues](https://github.com/shortalex12333/Cloud_PMS/issues)

---

## 📞 **Support**

Questions about workflow? Ask in:
- GitHub Discussions
- Slack #celesteos-dev
- Tag @lead-engineer in PR comments

---

**Remember:** This workflow exists to prevent chaos, not create it. Follow the rules and we all ship faster. 🚀
