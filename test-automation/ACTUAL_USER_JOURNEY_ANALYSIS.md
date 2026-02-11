# Actual User Journey vs What Was Tested

**Date:** 2026-02-11
**Issue:** Tested backend APIs without validating frontend UI exposes these features

---

## The Problem

**You're right:** I tested image upload/update/delete API endpoints extensively (Day 3, 9 tests) but **the frontend has NO UI for users to upload part images**. The "+" button or upload feature **doesn't exist in the UI**.

This is a critical gap - testing backend endpoints that users can't access is meaningless for production readiness.

---

## What Users ACTUALLY See

### 1. Main Interface (Single Surface Design)

**URL:** `/` (one page, no navigation)

**Components:**
- **SpotlightSearch** - Centered search bar (like macOS Spotlight)
- **Search Results** - Displayed inline below search bar
- **ContextPanel** - Slides from right for detail views
- **EmailOverlay** - Slides from left for email integration

### 2. User Journey: Searching for Parts

```
1. User types in search bar: "oil filter"
2. Results appear below with PartCard components
3. PartCard shows:
   ✅ Part name, part number
   ✅ Stock quantity, min stock level
   ✅ Location (deck, room, storage)
   ✅ Supplier, unit cost
   ✅ Action buttons (from backend MicroActions)
   ❌ NO IMAGE DISPLAY
   ❌ NO IMAGE UPLOAD BUTTON
   ❌ NO "+" BUTTON
```

### 3. User Journey: Adding a New Part

```
1. User searches or clicks "Add Part" action
2. AddPartModal opens
3. Modal shows form fields:
   ✅ Part name, part number
   ✅ Initial stock quantity
   ✅ Min stock level
   ✅ Location (general, deck, room, storage)
   ✅ Category (dropdown)
   ✅ Unit cost, supplier
   ❌ NO IMAGE UPLOAD FIELD
   ❌ NO FILE ATTACHMENT FIELD
   ❌ NO "Add Image" BUTTON
```

**Code Evidence:**
```typescript
// apps/web/src/components/modals/AddPartModal.tsx
// Lines 35-47: Form schema
const addPartSchema = z.object({
  part_name: z.string(),
  part_number: z.string(),
  stock_quantity: z.coerce.number(),
  min_stock_level: z.coerce.number(),
  location: z.string(),
  // ... other fields
  // ❌ NO image field
  // ❌ NO file field
});
```

### 4. User Journey: Viewing Part Details

```
1. User clicks on a part from search results
2. ContextPanel slides open from right
3. Detail view shows:
   ✅ Part information (name, number, stock)
   ✅ Location details
   ✅ Action buttons
   ❌ NO IMAGE GALLERY
   ❌ NO IMAGE VIEWER
   ❌ NO "Upload Image" BUTTON
```

---

## What I Tested (Day 3) vs What Exists

| Test | Backend API | Frontend UI | User Can Access? |
|------|-------------|-------------|------------------|
| **Upload part image** | ✅ Endpoint exists: `/v1/parts/upload-image` | ❌ No upload button | ❌ NO |
| **Update part image** | ✅ Endpoint exists: `/v1/parts/update-image` | ❌ No update UI | ❌ NO |
| **Delete part image** | ✅ Endpoint exists: `/v1/parts/delete-image` | ❌ No delete UI | ❌ NO |
| **View part images** | ❓ Unknown | ❌ No image display | ❌ NO |

**Conclusion:** I tested 9 endpoints that **users cannot access** because the UI doesn't exist.

---

## Actual User Capabilities (What Users CAN Do)

Based on frontend code analysis:

### ✅ Users CAN:

1. **Search** - Type queries in SpotlightSearch bar
2. **View Parts** - See search results with PartCard components
3. **Add Parts** - Open AddPartModal and fill form (no image)
4. **View Part Details** - Click part to open ContextPanel
5. **Execute Actions** - Click action buttons from backend suggestions:
   - Order part (add to shopping list)
   - Log usage
   - Edit quantity
   - Link to work order
   - Suggest parts

### ❌ Users CANNOT:

1. **Upload images** - No UI element exists
2. **View images** - Part cards show no images
3. **Update images** - No edit image button
4. **Delete images** - No delete image button
5. **Attach documents** - No file upload (except for receiving documents)

---

## Where Image Upload DOES Exist

**Found only 1 file upload UI:**

```
apps/web/src/components/receiving/ReceivingDocumentUpload.tsx
```

This is for **receiving documents** (shipment receipts, invoices), NOT part images.

**User Journey:**
```
1. User navigates to receiving workflow
2. Can upload PDFs/images for shipment documentation
3. Completely separate from parts inventory
```

---

## The Missing Features

### What SHOULD Exist (But Doesn't)

#### 1. PartCard Component Should Show:
```typescript
// Current (apps/web/src/components/cards/PartCard.tsx)
<div className="part-card">
  <Package icon /> {/* Generic icon */}
  <h3>{part.part_name}</h3>
  <p>P/N: {part.part_number}</p>
  // ❌ NO IMAGE DISPLAY
</div>

// Should be:
<div className="part-card">
  {part.image_url ? (
    <img src={part.image_url} alt={part.part_name} />
  ) : (
    <Package icon />
  )}
  <h3>{part.part_name}</h3>
  // ✅ + Button to upload/change image
  <button onClick={handleImageUpload}>
    <Plus /> Add Image
  </button>
</div>
```

#### 2. AddPartModal Should Include:
```typescript
// Current: NO image field
// Should add:
<div className="space-y-2">
  <Label htmlFor="image">Part Image</Label>
  <Input
    id="image"
    type="file"
    accept="image/png,image/jpeg,image/webp"
    onChange={handleImageUpload}
  />
  <p className="text-xs text-muted-foreground">
    Upload photo of part (max 5MB)
  </p>
</div>
```

#### 3. PartDetailView Should Show:
```typescript
// Should create: apps/web/src/components/parts/PartDetailView.tsx
<div className="part-detail">
  {/* Image gallery */}
  <div className="images">
    {part.images.map(img => (
      <img key={img.id} src={img.url} />
    ))}
    {/* + Button */}
    <button onClick={handleAddImage}>
      <Plus /> Add Image
    </button>
  </div>
</div>
```

---

## What Should Have Been Tested

Instead of testing isolated backend endpoints, I should have tested:

### Real User Journeys

#### Journey 1: "Find oil filter and order more"
```
1. ✅ User types "oil filter" in search
2. ✅ Results appear with PartCard
3. ✅ User sees stock level (e.g., "2 units, min 5")
4. ✅ User clicks "Order Part" button
5. ✅ Shopping list modal opens
6. ✅ User fills quantity and submits
7. ✅ Success toast appears
8. ✅ Shopping list item created in DB
```

#### Journey 2: "Add new part to inventory"
```
1. ✅ User searches or clicks "Add Part" action
2. ✅ AddPartModal opens
3. ✅ User fills: name, part number, stock, location
4. ✅ User submits form
5. ✅ Part created in DB
6. ✅ Modal closes
7. ✅ Search refreshes to show new part
```

#### Journey 3: "View part details and check stock"
```
1. ✅ User clicks on part from results
2. ✅ ContextPanel slides open
3. ✅ Part details displayed
4. ✅ User sees available actions
5. ✅ User can execute actions
```

#### Journey 4: "Upload part image" ❌ NOT POSSIBLE
```
1. User wants to attach image to part
2. ❌ No upload button in PartCard
3. ❌ No upload field in AddPartModal
4. ❌ No image tab in detail view
5. ❌ BLOCKED - Feature doesn't exist in UI
```

---

## Frontend Features That DO Exist (What to Test)

### 1. Search & Results
- **Component:** `SpotlightSearch.tsx`
- **Test:** Type query, verify results appear
- **Actions:** Click result, verify detail view opens

### 2. Part Management
- **Components:** `PartCard.tsx`, `AddPartModal.tsx`
- **Test:** Add new part, verify form validation
- **Test:** Submit form, verify part appears in search

### 3. Action Execution
- **Component:** `ActionButton.tsx`
- **Test:** Click "Order Part", verify modal opens
- **Test:** Submit action, verify backend call succeeds

### 4. Shopping List
- **Components:** Shopping list modals
- **Test:** Add part to shopping list
- **Test:** View shopping list items

### 5. Work Orders
- **Components:** Work order modals
- **Test:** Create work order
- **Test:** Link parts to work order

### 6. RBAC
- **Test:** Login as different roles
- **Test:** Verify action buttons filtered by role
- **Test:** Captain sees all actions, Crew sees limited

---

## Correct Testing Approach

### What I Should Do Going Forward:

1. **Map All Frontend Components**
   - Identify every modal, card, panel
   - Document what actions are possible
   - List all buttons, forms, inputs

2. **Test Real User Journeys**
   - Start from search bar
   - Follow visual UI elements
   - Click buttons that actually exist
   - Verify end-to-end flows work

3. **Validate UI ↔ Backend Integration**
   - User clicks "Order Part" → Backend creates shopping_list_item
   - User clicks "Create Work Order" → Backend creates work_order
   - NOT: Test backend `/upload-image` when no upload button exists

4. **Document Missing Features**
   - Image upload/display for parts
   - Document attachment for work orders
   - Any backend API with no frontend

5. **Test What Users See**
   - Verify visual elements render
   - Check button states (enabled/disabled)
   - Validate error messages appear
   - Confirm success toasts show

---

## Recommended Next Steps

### Immediate Testing Priorities

1. **User Journey Testing (E2E with Playwright)**
   ```
   ✅ Already done in Day 4:
   - Login as Captain/HOD/Crew
   - Search for parts/work orders
   - View results
   - Execute actions

   ❌ Need to add:
   - Add new part flow
   - Create work order flow
   - Add part to shopping list flow
   - Link parts to work order flow
   ```

2. **Visual Regression Testing**
   - Capture screenshots of all components
   - Verify layouts render correctly
   - Check responsive design
   - Validate dark/light themes

3. **Frontend Unit Tests**
   - Test form validation logic
   - Test search debouncing
   - Test action button states
   - Test modal open/close

### Feature Gap Documentation

**Create tickets for:**
1. Add image upload to PartCard component
2. Add image field to AddPartModal
3. Create PartImageGallery component
4. Add image viewer to PartDetailView
5. Implement image upload API integration

### Re-prioritize Testing

**STOP testing:**
- Backend endpoints with no UI
- API features users can't access
- Isolated API calls

**START testing:**
- Complete user journeys
- UI interactions that exist
- Frontend → Backend integration for visible features
- Visual rendering and UX flows

---

## Lessons Learned

### 1. Backend API ≠ User Capability
- Just because an endpoint exists doesn't mean users can use it
- Always verify frontend UI exposes the feature

### 2. Test From User Perspective
- Start from what users see (UI)
- Follow clickable elements
- Verify journeys, not isolated endpoints

### 3. Document Feature Gaps
- Backend has image upload API
- Frontend has NO image upload UI
- Gap = users can't upload images (blocked feature)

### 4. Integration Testing > API Testing
- User clicks button → Should trigger correct backend call
- More valuable than testing API endpoint in isolation

### 5. Understand the Architecture
- Single-page app (/)
- SpotlightSearch as primary interface
- Modal-based workflows
- No traditional navigation

---

## Summary

**What I tested (Day 3):** Backend image upload APIs (9 tests)

**What users can do:** Nothing related to images - NO UI exists

**What I should have tested:**
- Complete user journeys from search → action → result
- UI elements that actually exist
- Integration between frontend buttons and backend APIs

**Action needed:**
1. Document all missing UI components (image upload, file upload)
2. Re-test based on real user capabilities
3. Map frontend components to backend APIs
4. Identify feature gaps (APIs with no UI)

**Your feedback is correct:** Testing backend endpoints users can't access is wasteful. Need to test the actual user experience, not isolated APIs.
