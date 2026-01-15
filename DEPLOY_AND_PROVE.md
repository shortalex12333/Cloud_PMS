# DEPLOY AND PROVE - Execute This Now

## STEP 1: COMMIT AND DEPLOY

```bash
cd /Users/celeste7/Documents/Cloud_PMS

# Stage everything
git add -A

# Commit cleanup + any remaining changes
git commit -m "chore: Remove obsolete docs, add project memory files"

# Push to main (triggers Vercel deploy)
git push origin main
```

Wait 2 minutes for Vercel to deploy.

---

## STEP 2: VERIFY DEPLOYMENT

Check Vercel deployment succeeded:
```bash
# Check deployment status
curl -s -o /dev/null -w "%{http_code}" https://app.celeste7.ai
# Should return 200
```

---

## STEP 3: PROVE IT WORKS - Manual E2E Test

### Login Test
```
1. Open https://app.celeste7.ai in browser
2. Login with:
   - Email: x@alex-short.com
   - Password: Password2!
3. Verify: Dashboard loads without errors
```

### Fault Card Test (Cluster 1)
```
1. Navigate to Faults page (or search for a fault)
2. Find any fault card
3. Verify these buttons appear:
   - Diagnose (should ALWAYS show)
   - Manual (should show if equipment linked)
   - History (should ALWAYS show)
   - Note (should ALWAYS show)
   - Photo (should ALWAYS show)
   - Create WO (should show if no WO exists)
   - Suggest Parts (should ONLY show if fault is "known" by AI)

4. Click "Diagnose" button
5. Verify: Modal opens, diagnosis runs, result displays

6. Click "Add Note" button
7. Verify: Modal opens, can type note, saves successfully
```

### Work Order Card Test (Cluster 2)
```
1. Navigate to Work Orders page
2. Find an OPEN work order
3. Verify these buttons appear:
   - Complete (only if status = open/in_progress)
   - Add Note
   - Add Photo
   - Assign (only if you're HOD role)

4. Click a button, verify it works
```

### Role-Based Test
```
1. As x@alex-short.com, check your role
2. If NOT HOD: "Assign Work Order" should be HIDDEN
3. If HOD: "Assign Work Order" should be VISIBLE
```

---

## STEP 4: CAPTURE EVIDENCE

For each test above, capture:
```
- Screenshot of buttons appearing on card
- Screenshot of modal opening
- Screenshot of success message
- Console log (F12 > Console) showing no errors
```

Save screenshots to: `/tmp/claude/verification_evidence/`

---

## STEP 5: REPORT RESULTS

Create a verification report:

```markdown
# Verification Report - [DATE]

## Deployment
- [ ] Git push succeeded
- [ ] Vercel deployment completed
- [ ] https://app.celeste7.ai returns 200

## Login
- [ ] Can login as x@alex-short.com
- [ ] Dashboard loads

## Fault Card (Cluster 1)
- [ ] Diagnose button visible
- [ ] Diagnose button works (modal opens, runs)
- [ ] Add Note button visible
- [ ] Add Note button works
- [ ] Suggest Parts only shows for known faults

## Work Order Card (Cluster 2)
- [ ] Buttons appear correctly
- [ ] At least one button works

## Role Filtering
- [ ] HOD-only buttons hidden for non-HOD users
- [ ] OR confirmed user IS HOD and sees all buttons

## Evidence
- Screenshots saved: [YES/NO]
- Console errors: [NONE / LIST THEM]
```

---

## STEP 6: FIX E2E TESTS (If Time)

If manual tests pass but GitHub E2E fails:
```bash
# Check what's failing
cd /Users/celeste7/Documents/Cloud_PMS
npx playwright test --headed

# Fix failing tests
# Tests may expect buttons that now only show conditionally
# Update test selectors to match new trigger logic
```

---

## SUCCESS CRITERIA

Deployment is PROVEN when:
- [ ] Code pushed to main
- [ ] Vercel shows successful deployment
- [ ] Can login on production
- [ ] At least 3 different buttons clicked and working
- [ ] Screenshots captured as evidence
- [ ] No console errors

**DO NOT claim success without completing these steps.**
