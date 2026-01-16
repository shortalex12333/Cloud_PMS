# FRONTEND COMPLETION PHASES (16-18)

**Prerequisite:** Phases 8-15 must be complete (backend production-ready)
**Goal:** Users can actually see and click microaction buttons in the UI

---

## PHASE 16: Frontend Button Implementation

### Description

Verify and implement all 57 microaction buttons in React components. Each button must:
- Appear in correct context (fault detail, WO detail, equipment detail, etc.)
- Call the correct backend handler via API
- Show loading state during execution
- Display success/error feedback
- Update UI after action completes

### Files to Read

```
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/spotlight/MicroactionButton.tsx
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/spotlight/SpotlightPreviewPane.tsx
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/microactions/handlers.ts (if exists)
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/api.ts
/Users/celeste7/Documents/Cloud_PMS/tests/fixtures/microaction_registry.ts (from Phase 11)
```

### Files to Create/Modify

```
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/microactions/index.ts
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/microactions/definitions.ts
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/microactions/executor.ts
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/microactions/ActionButton.tsx
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/microactions/ActionModal.tsx
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/microactions/ActionFeedback.tsx
```

### Button Categories by Context

| Context | Component | Buttons Required |
|---------|-----------|------------------|
| Fault Detail | FaultDetailView.tsx | diagnose_fault, add_fault_photo, add_fault_note, create_work_order_from_fault, mark_fault_false_alarm, close_fault, reopen_fault |
| Work Order Detail | WorkOrderDetailView.tsx | start_work_order, add_wo_part, add_wo_hours, add_wo_note, add_work_order_photo, assign_work_order, mark_work_order_complete, cancel_work_order |
| Equipment Detail | EquipmentDetailView.tsx | update_equipment_status, add_equipment_note, show_manual_section, view_equipment_history |
| Part Detail | PartDetailView.tsx | check_stock_level, log_part_usage, add_to_shopping_list |
| Handover | HandoverView.tsx | add_to_handover, edit_handover_section, regenerate_handover_summary |
| Shopping List | ShoppingListView.tsx | delete_shopping_item, approve_shopping_item |
| Purchase Order | PurchaseOrderView.tsx | create_purchase_request, order_part, approve_purchase |
| Compliance | ComplianceView.tsx | update_hours_of_rest, view_hours_of_rest |

### Tasks

1. **Audit existing buttons:**
   ```bash
   # Find all MicroactionButton usages
   grep -r "MicroactionButton\|data-action=" apps/web/src/components/ --include="*.tsx"

   # Find all executeAction calls
   grep -r "executeAction\|/v1/actions/execute" apps/web/src/ --include="*.ts" --include="*.tsx"
   ```

2. **Create microaction definitions file:**
   ```typescript
   // apps/web/src/lib/microactions/definitions.ts

   export interface MicroactionDefinition {
     id: string;
     label: string;
     icon: string;
     context: 'fault' | 'work_order' | 'equipment' | 'part' | 'handover' | 'shopping' | 'purchase' | 'compliance';
     requiredFields: string[];
     optionalFields?: string[];
     confirmationRequired: boolean;
     confirmationMessage?: string;
     successMessage: string;
     dangerLevel: 'safe' | 'caution' | 'danger';
   }

   export const MICROACTION_DEFINITIONS: Record<string, MicroactionDefinition> = {
     diagnose_fault: {
       id: 'diagnose_fault',
       label: 'Diagnose',
       icon: 'Stethoscope',
       context: 'fault',
       requiredFields: ['fault_id', 'diagnosis_text'],
       confirmationRequired: false,
       successMessage: 'Diagnosis recorded',
       dangerLevel: 'safe',
     },
     delete_document: {
       id: 'delete_document',
       label: 'Delete',
       icon: 'Trash2',
       context: 'document',
       requiredFields: ['document_id'],
       confirmationRequired: true,
       confirmationMessage: 'Are you sure you want to delete this document?',
       successMessage: 'Document deleted',
       dangerLevel: 'danger',
     },
     // ... all 57 actions
   };
   ```

3. **Create action executor:**
   ```typescript
   // apps/web/src/lib/microactions/executor.ts

   import { MICROACTION_DEFINITIONS } from './definitions';

   export async function executeAction(
     actionId: string,
     payload: Record<string, any>,
     context: { yacht_id: string; user_id: string }
   ): Promise<ActionResult> {
     const definition = MICROACTION_DEFINITIONS[actionId];
     if (!definition) {
       throw new Error(`Unknown action: ${actionId}`);
     }

     // Validate required fields
     for (const field of definition.requiredFields) {
       if (!(field in payload)) {
         throw new Error(`Missing required field: ${field}`);
       }
     }

     // Execute via API
     const response = await fetch(`${API_URL}/v1/actions/execute`, {
       method: 'POST',
       headers: {
         'Authorization': `Bearer ${getToken()}`,
         'Content-Type': 'application/json',
       },
       body: JSON.stringify({
         action: actionId,
         context,
         payload,
       }),
     });

     if (!response.ok) {
       const error = await response.json();
       throw new ActionError(error.message, error.code);
     }

     return response.json();
   }
   ```

4. **Create reusable ActionButton component:**
   ```typescript
   // apps/web/src/components/microactions/ActionButton.tsx

   interface ActionButtonProps {
     actionId: string;
     entityId: string;
     entityType: 'fault' | 'work_order' | 'equipment' | etc;
     payload?: Record<string, any>;
     onSuccess?: (result: any) => void;
     onError?: (error: Error) => void;
     variant?: 'primary' | 'secondary' | 'danger';
     size?: 'sm' | 'md' | 'lg';
   }

   export function ActionButton({
     actionId,
     entityId,
     entityType,
     payload = {},
     onSuccess,
     onError,
     variant = 'secondary',
     size = 'md',
   }: ActionButtonProps) {
     const [loading, setLoading] = useState(false);
     const [showConfirm, setShowConfirm] = useState(false);
     const { user } = useAuth();

     const definition = MICROACTION_DEFINITIONS[actionId];
     if (!definition) return null;

     const handleClick = async () => {
       if (definition.confirmationRequired) {
         setShowConfirm(true);
         return;
       }
       await execute();
     };

     const execute = async () => {
       setLoading(true);
       try {
         const result = await executeAction(actionId, {
           ...payload,
           [`${entityType}_id`]: entityId,
         }, {
           yacht_id: user.yachtId,
           user_id: user.id,
         });

         toast.success(definition.successMessage);
         onSuccess?.(result);
       } catch (error) {
         toast.error(error.message);
         onError?.(error);
       } finally {
         setLoading(false);
         setShowConfirm(false);
       }
     };

     return (
       <>
         <Button
           onClick={handleClick}
           disabled={loading}
           variant={variant}
           size={size}
           data-action={actionId}
         >
           {loading ? <Spinner /> : <Icon name={definition.icon} />}
           {definition.label}
         </Button>

         {showConfirm && (
           <ConfirmModal
             title={`Confirm ${definition.label}`}
             message={definition.confirmationMessage}
             onConfirm={execute}
             onCancel={() => setShowConfirm(false)}
             danger={definition.dangerLevel === 'danger'}
           />
         )}
       </>
     );
   }
   ```

5. **Wire buttons into detail views:**
   ```typescript
   // Example: apps/web/src/components/faults/FaultDetailView.tsx

   import { ActionButton } from '@/components/microactions/ActionButton';

   export function FaultDetailView({ fault }: { fault: Fault }) {
     return (
       <div>
         {/* Fault details */}
         <h1>{fault.title}</h1>

         {/* Action buttons based on status */}
         <div className="action-buttons">
           {fault.status === 'open' && (
             <>
               <ActionButton
                 actionId="diagnose_fault"
                 entityId={fault.id}
                 entityType="fault"
               />
               <ActionButton
                 actionId="add_fault_photo"
                 entityId={fault.id}
                 entityType="fault"
               />
               <ActionButton
                 actionId="create_work_order_from_fault"
                 entityId={fault.id}
                 entityType="fault"
                 variant="primary"
               />
             </>
           )}

           {fault.status === 'diagnosed' && (
             <>
               <ActionButton
                 actionId="mark_fault_false_alarm"
                 entityId={fault.id}
                 entityType="fault"
               />
               <ActionButton
                 actionId="close_fault"
                 entityId={fault.id}
                 entityType="fault"
               />
             </>
           )}

           {fault.status === 'closed' && (
             <ActionButton
               actionId="reopen_fault"
               entityId={fault.id}
               entityType="fault"
             />
           )}
         </div>
       </div>
     );
   }
   ```

### Verification

```bash
# Count ActionButton usages (should be 57+)
grep -r "ActionButton\|data-action=" apps/web/src/ --include="*.tsx" | wc -l

# Run component tests
npm run test -- --grep="ActionButton"

# Visual verification
npm run dev
# Navigate to each entity type, verify buttons appear
```

### Prompt for Claude

```
Read /Users/celeste7/Documents/Cloud_PMS/PHASE_16_17_18_FRONTEND.md

Execute PHASE 16: Frontend Button Implementation

PROTOCOL ACTIVE: MICROACTIONS_COMPLETION_PROTOCOL

Before writing ANY code:
1. Enter deep thinking mode
2. git checkout -b claude/phase-16-frontend-buttons
3. Audit existing button implementations
4. Read all files listed in Phase 16

Step-by-step:
1. grep for existing MicroactionButton and data-action usages
2. Read SpotlightPreviewPane.tsx - understand current button rendering
3. Create apps/web/src/lib/microactions/definitions.ts with all 57 actions
4. Create apps/web/src/lib/microactions/executor.ts
5. Create apps/web/src/components/microactions/ActionButton.tsx
6. Create apps/web/src/components/microactions/ConfirmModal.tsx
7. Wire ActionButton into FaultDetailView.tsx
8. Wire ActionButton into WorkOrderDetailView.tsx
9. Wire ActionButton into EquipmentDetailView.tsx
10. Wire remaining detail views
11. Run: npm run build (verify no TypeScript errors)
12. Run: npm run test

Git workflow:
- Branch: claude/phase-16-frontend-buttons
- Commits: feat(ui): {description}
- Merge to main when build passes

Report:
- Files created/modified with line counts
- Button count per context
- Build status
- Any missing contexts

Take your time. This is user-facing UI code.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## PHASE 17: Situation Awareness Integration

### Description

Implement AI-driven context awareness that intelligently suggests relevant actions based on:
- Current entity being viewed
- Entity state (status, flags, relationships)
- User role and permissions
- Recent activity and patterns
- Time-based triggers (overdue items, upcoming maintenance)

### Files to Read

```
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/contexts/AuthContext.tsx (user role)
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/microactions/definitions.ts (from Phase 16)
/Users/celeste7/Documents/Cloud_PMS/apps/api/services/trigger_service.py (from Phase 10)
/Users/celeste7/Desktop/Cloud_PMS_docs_v2/03_MICROACTIONS/ACTION_OFFERING_RULES.md
```

### Files to Create

```
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/situation/index.ts
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/situation/analyzer.ts
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/situation/suggestions.ts
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/situation/SituationPanel.tsx
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/situation/ActionSuggestion.tsx
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/hooks/useSituation.ts
```

### Situation Types

| Situation | Trigger | Suggested Actions | Priority |
|-----------|---------|-------------------|----------|
| FAULT_OPEN | Viewing open fault | diagnose_fault, add_fault_photo | HIGH |
| FAULT_DIAGNOSED | Viewing diagnosed fault | create_work_order_from_fault, mark_fault_false_alarm | HIGH |
| WO_READY_TO_START | Viewing planned WO with parts available | start_work_order | HIGH |
| WO_IN_PROGRESS | Viewing in-progress WO | add_wo_hours, add_wo_note, mark_work_order_complete | MEDIUM |
| WO_OVERDUE | WO past due date | assign_work_order (if unassigned), escalate | CRITICAL |
| LOW_STOCK | Part below minimum | add_to_shopping_list, create_purchase_request | MEDIUM |
| MAINTENANCE_DUE | Equipment maintenance upcoming | create_work_order | MEDIUM |
| HOR_INCOMPLETE | Today's hours not logged | update_hours_of_rest | HIGH |
| HANDOVER_PENDING | Items flagged for handover | add_to_handover, regenerate_handover_summary | MEDIUM |

### Tasks

1. **Create situation analyzer:**
   ```typescript
   // apps/web/src/lib/situation/analyzer.ts

   export interface Situation {
     id: string;
     type: SituationType;
     priority: 'low' | 'medium' | 'high' | 'critical';
     entity: {
       type: string;
       id: string;
       data: any;
     };
     suggestedActions: string[];
     message: string;
     context: Record<string, any>;
   }

   export function analyzeSituation(
     entityType: string,
     entity: any,
     userRole: string,
     triggers: TriggerResult[]
   ): Situation[] {
     const situations: Situation[] = [];

     // Fault situations
     if (entityType === 'fault') {
       if (entity.status === 'open') {
         situations.push({
           id: `fault-open-${entity.id}`,
           type: 'FAULT_OPEN',
           priority: entity.severity === 'critical' ? 'critical' : 'high',
           entity: { type: 'fault', id: entity.id, data: entity },
           suggestedActions: ['diagnose_fault', 'add_fault_photo', 'add_fault_note'],
           message: `This fault needs diagnosis. ${entity.severity === 'critical' ? 'CRITICAL SEVERITY.' : ''}`,
           context: { severity: entity.severity },
         });
       }

       if (entity.status === 'diagnosed' && !entity.work_order_id) {
         situations.push({
           id: `fault-needs-wo-${entity.id}`,
           type: 'FAULT_DIAGNOSED',
           priority: 'high',
           entity: { type: 'fault', id: entity.id, data: entity },
           suggestedActions: ['create_work_order_from_fault', 'mark_fault_false_alarm'],
           message: 'Fault diagnosed. Create a work order or mark as false alarm.',
           context: { diagnosis: entity.metadata?.diagnosis },
         });
       }
     }

     // Work order situations
     if (entityType === 'work_order') {
       const isOverdue = new Date(entity.due_date) < new Date();

       if (entity.status === 'planned' && isOverdue) {
         situations.push({
           id: `wo-overdue-${entity.id}`,
           type: 'WO_OVERDUE',
           priority: 'critical',
           entity: { type: 'work_order', id: entity.id, data: entity },
           suggestedActions: ['start_work_order', 'assign_work_order'],
           message: `Work order is OVERDUE by ${daysSince(entity.due_date)} days.`,
           context: { due_date: entity.due_date, days_overdue: daysSince(entity.due_date) },
         });
       }

       if (entity.status === 'in_progress') {
         situations.push({
           id: `wo-in-progress-${entity.id}`,
           type: 'WO_IN_PROGRESS',
           priority: 'medium',
           entity: { type: 'work_order', id: entity.id, data: entity },
           suggestedActions: ['add_wo_hours', 'add_wo_part', 'add_wo_note', 'mark_work_order_complete'],
           message: 'Work order in progress. Log hours, parts, or mark complete.',
           context: { progress: entity.progress_percent },
         });
       }
     }

     // Add trigger-based situations
     for (const trigger of triggers) {
       situations.push(triggerToSituation(trigger));
     }

     // Sort by priority
     return situations.sort((a, b) =>
       PRIORITY_ORDER[b.priority] - PRIORITY_ORDER[a.priority]
     );
   }
   ```

2. **Create situation hook:**
   ```typescript
   // apps/web/src/hooks/useSituation.ts

   export function useSituation(entityType: string, entityId: string) {
     const { user } = useAuth();
     const [situations, setSituations] = useState<Situation[]>([]);
     const [loading, setLoading] = useState(true);

     useEffect(() => {
       async function analyze() {
         setLoading(true);

         // Fetch entity data
         const entity = await fetchEntity(entityType, entityId);

         // Fetch active triggers
         const triggers = await fetchTriggers(user.yachtId);

         // Analyze situation
         const results = analyzeSituation(
           entityType,
           entity,
           user.role,
           triggers
         );

         setSituations(results);
         setLoading(false);
       }

       analyze();
     }, [entityType, entityId, user]);

     return { situations, loading };
   }
   ```

3. **Create SituationPanel component:**
   ```typescript
   // apps/web/src/components/situation/SituationPanel.tsx

   export function SituationPanel({ entityType, entityId }: Props) {
     const { situations, loading } = useSituation(entityType, entityId);

     if (loading) return <SituationSkeleton />;
     if (situations.length === 0) return null;

     return (
       <div className="situation-panel">
         <h3>
           <Lightbulb className="icon" />
           Suggested Actions
         </h3>

         {situations.map((situation) => (
           <SituationCard key={situation.id} situation={situation}>
             <p className={`priority-${situation.priority}`}>
               {situation.message}
             </p>

             <div className="suggested-actions">
               {situation.suggestedActions.map((actionId) => (
                 <ActionButton
                   key={actionId}
                   actionId={actionId}
                   entityId={situation.entity.id}
                   entityType={situation.entity.type}
                   size="sm"
                 />
               ))}
             </div>
           </SituationCard>
         ))}
       </div>
     );
   }
   ```

4. **Integrate into detail views:**
   ```typescript
   // apps/web/src/components/faults/FaultDetailView.tsx

   export function FaultDetailView({ fault }: Props) {
     return (
       <div className="fault-detail">
         {/* Situation awareness panel */}
         <SituationPanel entityType="fault" entityId={fault.id} />

         {/* Rest of fault details */}
         <FaultHeader fault={fault} />
         <FaultBody fault={fault} />
         <FaultActions fault={fault} />
       </div>
     );
   }
   ```

### Verification

```bash
# Run situation analyzer tests
npm run test -- --grep="situation"

# Visual verification
npm run dev
# View fault with status=open -> should see "Needs diagnosis" suggestion
# View overdue WO -> should see "OVERDUE" critical situation
```

### Prompt for Claude

```
Read /Users/celeste7/Documents/Cloud_PMS/PHASE_16_17_18_FRONTEND.md

Execute PHASE 17: Situation Awareness Integration

PROTOCOL ACTIVE: MICROACTIONS_COMPLETION_PROTOCOL

Before writing ANY code:
1. Enter deep thinking mode
2. git checkout -b claude/phase-17-situation-awareness
3. Read ACTION_OFFERING_RULES.md thoroughly
4. Understand trigger service from Phase 10

Step-by-step:
1. Read AuthContext.tsx - understand user role access
2. Read definitions.ts from Phase 16 - understand action definitions
3. Read trigger_service.py - understand backend triggers
4. Create apps/web/src/lib/situation/analyzer.ts with all situation types
5. Create apps/web/src/lib/situation/suggestions.ts
6. Create apps/web/src/hooks/useSituation.ts
7. Create apps/web/src/components/situation/SituationPanel.tsx
8. Create apps/web/src/components/situation/SituationCard.tsx
9. Integrate SituationPanel into FaultDetailView.tsx
10. Integrate SituationPanel into WorkOrderDetailView.tsx
11. Integrate SituationPanel into EquipmentDetailView.tsx
12. Run: npm run build
13. Test with different entity states

Git workflow:
- Branch: claude/phase-17-situation-awareness
- Commits: feat(situation): {description}
- Merge to main when passing

Report:
- Situation types implemented
- Integration points
- Test scenarios verified

Take your time. This is AI-assisted UX.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## PHASE 18: End-to-End User Flow Testing

### Description

Complete user journey testing from login to action execution. Verify the entire flow works on real devices and handles errors gracefully.

### Files to Read

```
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/microactions/*.spec.ts (existing tests)
/Users/celeste7/Documents/Cloud_PMS/playwright.config.ts
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/microactions/*.tsx (from Phase 16)
```

### Files to Create

```
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/user-flows/fault-lifecycle.spec.ts
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/user-flows/work-order-lifecycle.spec.ts
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/user-flows/inventory-flow.spec.ts
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/user-flows/handover-flow.spec.ts
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/user-flows/error-handling.spec.ts
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/user-flows/mobile-responsive.spec.ts
```

### User Flow Test Cases

| Flow | Steps | Success Criteria |
|------|-------|------------------|
| Fault Lifecycle | Login → Report fault → Diagnose → Create WO → Complete WO → Close fault | All status transitions work, audit trail created |
| Work Order Lifecycle | Login → Create WO → Add parts → Start → Log hours → Complete | WO progresses through all states |
| Inventory Flow | Login → Check stock → Add to shopping → Approve → Create PO | Parts flow through procurement |
| Handover Flow | Login → Add items → Edit section → Regenerate summary | Handover document updates |
| Error Handling | Trigger network error, validation error, permission error | User sees clear error messages |
| Mobile Responsive | Run all flows on mobile viewport | Buttons accessible, modals fit screen |

### Tasks

1. **Create fault lifecycle test:**
   ```typescript
   // tests/e2e/user-flows/fault-lifecycle.spec.ts

   import { test, expect } from '@playwright/test';

   test.describe('Fault Lifecycle - Full User Journey', () => {

     test('complete fault lifecycle: report → diagnose → WO → close', async ({ page }) => {
       // Step 1: Login
       await page.goto('/login');
       await page.fill('input[type="email"]', process.env.TEST_USER_EMAIL!);
       await page.fill('input[type="password"]', process.env.TEST_USER_PASSWORD!);
       await page.click('button[type="submit"]');
       await page.waitForURL(/\/(search|dashboard)/);

       // Step 2: Report new fault
       await page.goto('/search');
       await page.click('[data-action="report_fault"]'); // Or navigate to fault creation

       await page.fill('[name="title"]', `E2E Test Fault - ${Date.now()}`);
       await page.fill('[name="description"]', 'Automated test fault');
       await page.selectOption('[name="severity"]', 'medium');
       await page.selectOption('[name="equipment_id"]', { index: 1 }); // First equipment
       await page.click('button[type="submit"]');

       // Verify fault created
       await expect(page.locator('.toast-success')).toContainText('Fault reported');
       const faultUrl = page.url();
       expect(faultUrl).toMatch(/\/faults\/[a-f0-9-]+/);

       // Step 3: Diagnose fault
       await expect(page.locator('[data-action="diagnose_fault"]')).toBeVisible();
       await page.click('[data-action="diagnose_fault"]');

       await page.fill('[name="diagnosis_text"]', 'E2E test diagnosis - component wear detected');
       await page.click('button:has-text("Submit Diagnosis")');

       await expect(page.locator('.toast-success')).toContainText('Diagnosis recorded');
       await expect(page.locator('[data-status]')).toContainText('diagnosed');

       // Step 4: Create work order from fault
       await expect(page.locator('[data-action="create_work_order_from_fault"]')).toBeVisible();
       await page.click('[data-action="create_work_order_from_fault"]');

       await page.fill('[name="wo_title"]', `WO for E2E Fault - ${Date.now()}`);
       await page.click('button:has-text("Create Work Order")');

       await expect(page.locator('.toast-success')).toContainText('Work order created');

       // Navigate to created WO
       await page.click('a:has-text("View Work Order")');
       await expect(page).toHaveURL(/\/work-orders\/[a-f0-9-]+/);

       // Step 5: Start work order
       await page.click('[data-action="start_work_order"]');
       await expect(page.locator('.toast-success')).toContainText('Work order started');
       await expect(page.locator('[data-status]')).toContainText('in_progress');

       // Step 6: Add hours
       await page.click('[data-action="add_wo_hours"]');
       await page.fill('[name="hours"]', '2');
       await page.fill('[name="description"]', 'E2E test work');
       await page.click('button:has-text("Log Hours")');
       await expect(page.locator('.toast-success')).toContainText('Hours logged');

       // Step 7: Complete work order
       await page.click('[data-action="mark_work_order_complete"]');
       await page.click('button:has-text("Confirm Complete")'); // Confirmation modal
       await expect(page.locator('.toast-success')).toContainText('completed');
       await expect(page.locator('[data-status]')).toContainText('completed');

       // Step 8: Go back to fault and close it
       await page.goto(faultUrl);
       await page.click('[data-action="close_fault"]');
       await page.click('button:has-text("Confirm Close")');
       await expect(page.locator('.toast-success')).toContainText('Fault closed');
       await expect(page.locator('[data-status]')).toContainText('closed');

       // Step 9: Verify audit trail
       await page.click('[data-tab="history"]');
       await expect(page.locator('.audit-entry')).toHaveCount({ minimum: 4 }); // report, diagnose, WO created, closed
     });

   });
   ```

2. **Create error handling tests:**
   ```typescript
   // tests/e2e/user-flows/error-handling.spec.ts

   test.describe('Error Handling - User Feedback', () => {

     test('shows validation error for empty required fields', async ({ page }) => {
       await login(page);
       await page.goto('/faults/new');

       // Submit without filling required fields
       await page.click('button[type="submit"]');

       // Should show validation errors
       await expect(page.locator('.field-error')).toContainText('Title is required');
       await expect(page.locator('.field-error')).toContainText('Severity is required');
     });

     test('shows permission error for unauthorized action', async ({ page }) => {
       await loginAs(page, 'member'); // Low-permission user
       await page.goto('/faults/some-fault-id');

       // Try to approve (member cannot approve)
       const approveButton = page.locator('[data-action="approve_purchase"]');

       // Button should either be hidden OR show error on click
       if (await approveButton.isVisible()) {
         await approveButton.click();
         await expect(page.locator('.toast-error')).toContainText('Permission denied');
       }
     });

     test('handles network error gracefully', async ({ page }) => {
       await login(page);
       await page.goto('/faults/some-fault-id');

       // Intercept API and return error
       await page.route('**/v1/actions/execute', (route) => {
         route.fulfill({ status: 500, body: JSON.stringify({ error: 'Server error' }) });
       });

       await page.click('[data-action="diagnose_fault"]');
       await page.fill('[name="diagnosis_text"]', 'Test');
       await page.click('button:has-text("Submit")');

       // Should show error toast, not crash
       await expect(page.locator('.toast-error')).toContainText('Something went wrong');

       // Modal should still be open for retry
       await expect(page.locator('.modal')).toBeVisible();
     });

     test('recovers from timeout', async ({ page }) => {
       await login(page);

       // Intercept API and delay response
       await page.route('**/v1/actions/execute', async (route) => {
         await new Promise(resolve => setTimeout(resolve, 35000)); // 35s delay
         route.fulfill({ status: 200, body: JSON.stringify({ success: true }) });
       });

       await page.goto('/faults/some-fault-id');
       await page.click('[data-action="add_fault_note"]');
       await page.fill('[name="note_text"]', 'Test note');
       await page.click('button:has-text("Add Note")');

       // Should show timeout message after 30s
       await expect(page.locator('.toast-error')).toContainText('Request timed out', { timeout: 35000 });
     });

   });
   ```

3. **Create mobile responsive tests:**
   ```typescript
   // tests/e2e/user-flows/mobile-responsive.spec.ts

   import { test, expect, devices } from '@playwright/test';

   const MOBILE_DEVICES = [
     devices['iPhone 13'],
     devices['iPhone SE'],
     devices['Pixel 5'],
     devices['iPad Mini'],
   ];

   for (const device of MOBILE_DEVICES) {
     test.describe(`Mobile: ${device.name}`, () => {
       test.use({ ...device });

       test('can complete fault reporting flow', async ({ page }) => {
         await login(page);
         await page.goto('/search');

         // Search input should be accessible
         await expect(page.locator('input[type="search"]')).toBeVisible();

         // Navigate to fault
         await page.fill('input[type="search"]', 'fault');
         await page.keyboard.press('Enter');
         await page.click('.search-result >> nth=0');

         // Action buttons should be visible and tappable
         const actionButton = page.locator('[data-action="diagnose_fault"]');
         if (await actionButton.isVisible()) {
           const box = await actionButton.boundingBox();
           expect(box!.height).toBeGreaterThanOrEqual(44); // Min touch target
           expect(box!.width).toBeGreaterThanOrEqual(44);
         }

         // Modal should fit screen
         await page.click('[data-action="add_fault_note"]');
         const modal = page.locator('.modal');
         await expect(modal).toBeVisible();

         const modalBox = await modal.boundingBox();
         const viewport = page.viewportSize()!;
         expect(modalBox!.width).toBeLessThanOrEqual(viewport.width);
         expect(modalBox!.height).toBeLessThanOrEqual(viewport.height);
       });

     });
   }
   ```

### Verification

```bash
# Run all user flow tests
npx playwright test tests/e2e/user-flows/ --reporter=html

# Run with UI for debugging
npx playwright test tests/e2e/user-flows/ --ui

# Run mobile tests specifically
npx playwright test tests/e2e/user-flows/mobile-responsive.spec.ts --reporter=html
```

### Prompt for Claude

```
Read /Users/celeste7/Documents/Cloud_PMS/PHASE_16_17_18_FRONTEND.md

Execute PHASE 18: End-to-End User Flow Testing

PROTOCOL ACTIVE: MICROACTIONS_COMPLETION_PROTOCOL

Before writing ANY code:
1. Enter deep thinking mode
2. git checkout -b claude/phase-18-e2e-user-flows
3. Review existing e2e tests for patterns
4. Understand Playwright configuration

Step-by-step:
1. Read existing microaction tests for patterns
2. Read playwright.config.ts for test setup
3. Create tests/e2e/user-flows/fault-lifecycle.spec.ts
4. Create tests/e2e/user-flows/work-order-lifecycle.spec.ts
5. Create tests/e2e/user-flows/inventory-flow.spec.ts
6. Create tests/e2e/user-flows/handover-flow.spec.ts
7. Create tests/e2e/user-flows/error-handling.spec.ts
8. Create tests/e2e/user-flows/mobile-responsive.spec.ts
9. Run: npx playwright test tests/e2e/user-flows/ --reporter=list
10. Fix any failures
11. Generate HTML report

Git workflow:
- Branch: claude/phase-18-e2e-user-flows
- Commits: test(e2e): {description}
- Merge to main when all tests pass

Report:
- Test files created
- Test count per file
- Pass/fail results
- Mobile device coverage
- Screenshots of failures (if any)

This is the FINAL testing phase. Be thorough.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## UPDATED EXECUTION CHECKLIST

| Phase | Description | Status | Blocker |
|-------|-------------|--------|---------|
| 8 | Wire missing handlers | NOT STARTED | None |
| 9 | Seed empty tables | NOT STARTED | Phase 8 |
| 10 | Implement triggers | NOT STARTED | Phase 8, 9 |
| 11 | Visibility matrix tests | NOT STARTED | Phase 8 |
| 12 | RLS permission tests | NOT STARTED | Phase 8 |
| 13 | Edge case tests | NOT STARTED | Phase 8 |
| 14 | GitHub CI workflow | NOT STARTED | Phase 11-13 |
| 15 | Production verification (Backend) | NOT STARTED | Phase 8-14 |
| **16** | **Frontend button implementation** | NOT STARTED | Phase 15 |
| **17** | **Situation awareness integration** | NOT STARTED | Phase 16 |
| **18** | **End-to-end user flow testing** | NOT STARTED | Phase 16-17 |

---

## FINAL COMPLETION CRITERIA

The system is **fully production-ready** when:

### Backend (Phase 8-15)
- [ ] 95+ handlers registered in dispatcher
- [ ] All empty tables seeded with test data
- [ ] Trigger logic implemented and tested
- [ ] 114 visibility tests passing
- [ ] RLS tests passing for all 5 roles
- [ ] Edge case tests passing
- [ ] CI workflow green on main branch
- [ ] Production smoke tests pass (10/10)
- [ ] Release tag v1.0.0-microactions created

### Frontend (Phase 16-18)
- [ ] All 57 action buttons implemented in UI
- [ ] ActionButton component with loading/error states
- [ ] ConfirmModal for dangerous actions
- [ ] Situation awareness panel integrated
- [ ] All user flow tests passing
- [ ] Mobile responsive tests passing
- [ ] Error handling tests passing
- [ ] Release tag v1.1.0-frontend created

---

**END OF FRONTEND PHASES**
