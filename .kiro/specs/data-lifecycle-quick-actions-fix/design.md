# Data Lifecycle Quick Actions Bugfix Design

## Overview

This design addresses the bug where quick action buttons in the data lifecycle management dashboard are non-functional. The buttons currently only log to console instead of opening appropriate modals or triggering actions. The fix will implement 6 modal components with flexible data flow support, allowing users to transfer data between any stages without enforcing a strict sequential process.

The key insight is that data lifecycle flow is flexible and non-linear - users can directly transfer data to any downstream stage, skip intermediate stages, and select target stages dynamically based on their workflow needs.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when users click any of the 6 quick action buttons, nothing happens except console logging
- **Property (P)**: The desired behavior - buttons should open modals with forms for data creation/transfer, support flexible stage selection, and update the dashboard after submission
- **Preservation**: Existing button display, hover effects, tab navigation, and sub-page functionality must remain unchanged
- **handleAction**: The function in `frontend/src/pages/DataLifecycle/index.tsx` that currently only logs to console
- **QuickActions**: The component that renders the 6 quick action buttons
- **Modal Components**: New components to be created for each quick action (CreateTempDataModal, AddToLibraryModal, etc.)
- **Flexible Data Flow**: The ability to transfer data directly to any downstream stage without following a strict sequential process

## Bug Details

### Bug Condition

The bug manifests when users click any of the 6 quick action buttons in the data lifecycle dashboard. The `handleAction` function is only logging to console instead of opening modals or triggering appropriate actions.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type { actionKey: string, userClick: boolean }
  OUTPUT: boolean
  
  RETURN input.actionKey IN ['createTempData', 'addToLibrary', 'submitReview', 
                              'createTask', 'createEnhancement', 'createTrial']
         AND input.userClick === true
         AND NOT modalOpened(input.actionKey)
END FUNCTION
```

### Examples

- User clicks "创建临时数据" button → Expected: Modal opens with form to create temp data → Actual: Only console.log('Quick action: createTempData')
- User clicks "添加到样本库" button → Expected: Modal opens to select data from any stage and add to library → Actual: Only console.log('Quick action: addToLibrary')
- User clicks "提交审核" button → Expected: Modal opens to select data and target stage for review → Actual: Only console.log('Quick action: submitReview')
- User clicks "创建标注任务" button → Expected: Modal opens to create annotation task with data source selection → Actual: Only console.log('Quick action: createTask')
- User clicks "创建增强任务" button → Expected: Modal opens to create enhancement task → Actual: Only console.log('Quick action: createEnhancement')
- User clicks "创建AI试算" button → Expected: Modal opens to create AI trial with flexible stage selection → Actual: Only console.log('Quick action: createTrial')

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Button display with icons, labels, and colors must remain unchanged
- Hover effects and visual feedback on buttons must continue to work
- Tab navigation between different lifecycle stages must remain unchanged
- Data tables and operations in sub-pages must continue to function correctly
- Permission checks for button visibility must remain unchanged

**Scope:**
All inputs that do NOT involve clicking the 6 quick action buttons should be completely unaffected by this fix. This includes:
- Navigation between tabs
- Data table operations (view, edit, delete)
- Existing modal operations in sub-pages
- Dashboard statistics display
- Recent activity display

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is clear:

1. **Incomplete Implementation**: The `handleAction` function in `QuickActions` component only contains a console.log statement and TODO comment
   - Current code: `console.log('Quick action:', key);`
   - Missing: Modal state management and modal components

2. **Missing Modal Components**: None of the 6 required modal components exist yet
   - CreateTempDataModal
   - AddToLibraryModal
   - SubmitReviewModal
   - CreateTaskModal
   - CreateEnhancementModal
   - CreateTrialModal

3. **No State Management**: No React state to control modal visibility for each action

4. **No API Integration**: Modal components need to call existing API methods from hooks but this integration is not implemented

## Correctness Properties

Property 1: Bug Condition - Quick Action Buttons Open Modals

_For any_ user click on a quick action button where the button key is one of ['createTempData', 'addToLibrary', 'submitReview', 'createTask', 'createEnhancement', 'createTrial'], the fixed handleAction function SHALL open the corresponding modal component with appropriate form fields and data source selection options.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Property 2: Preservation - Non-Quick-Action Interactions

_For any_ user interaction that is NOT a click on one of the 6 quick action buttons (tab navigation, table operations, other buttons), the fixed code SHALL produce exactly the same behavior as the original code, preserving all existing functionality for dashboard display, navigation, and sub-page operations.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

Property 3: Flexible Data Flow - Stage Selection

_For any_ modal that supports data transfer (AddToLibraryModal, SubmitReviewModal, CreateTaskModal, CreateEnhancementModal, CreateTrialModal), the modal SHALL allow users to select data from any available stage and optionally select a target stage, without enforcing a strict sequential flow.

**Validates: Requirements 2.7, 2.8**

## Fix Implementation

### Changes Required

**File**: `frontend/src/pages/DataLifecycle/index.tsx`

**Component**: `QuickActions`

**Specific Changes**:

1. **Add Modal State Management**:
   - Add state variables to control visibility of each modal
   - Add handler functions to open/close modals
   - Pass state and handlers to modal components

2. **Implement Modal Components** (create new files in `frontend/src/components/DataLifecycle/`):
   - `CreateTempDataModal.tsx` - Form to create new temporary data
   - `AddToLibraryModal.tsx` - Select data from any stage and add to sample library
   - `SubmitReviewModal.tsx` - Select data and target stage for review submission
   - `CreateTaskModal.tsx` - Create annotation task with data source selection
   - `CreateEnhancementModal.tsx` - Create enhancement task with configuration
   - `CreateTrialModal.tsx` - Create AI trial with flexible stage selection

3. **Update handleAction Function**:
   - Replace console.log with modal open logic
   - Use switch/case or object mapping to open correct modal

4. **Integrate with Existing Hooks**:
   - Use `useTempData`, `useSampleLibrary`, `useReview`, `useAnnotationTask`, `useEnhancement`, `useAITrial` hooks
   - Call appropriate create/submit methods on form submission
   - Refresh dashboard data after successful operations

5. **Add Internationalization**:
   - All modal titles, labels, placeholders, and messages must use `t()` function
   - Translation keys already exist in `frontend/src/locales/zh/dataLifecycle.json` and `frontend/src/locales/en/dataLifecycle.json`

### Modal Component Specifications

#### 1. CreateTempDataModal
- **Purpose**: Create new temporary data entry
- **Form Fields**:
  - Name (required, text input)
  - Content (required, JSON editor or textarea)
  - Metadata (optional, JSON editor)
- **API**: `useTempData().createTempData()`
- **Validation**: Name required, content must be valid JSON

#### 2. AddToLibraryModal
- **Purpose**: Select data from any stage and add to sample library
- **Form Fields**:
  - Source Stage (select: 临时数据, 已标注, 已增强)
  - Data Selection (table with checkboxes, filtered by source stage)
  - Description (optional, textarea)
  - Data Type (select)
- **API**: `useSampleLibrary().addToLibrary(dataId)`
- **Validation**: At least one data item selected
- **Flexible Flow**: Users can select data from any available stage

#### 3. SubmitReviewModal
- **Purpose**: Submit data for review with target stage selection
- **Form Fields**:
  - Source Stage (select: any stage)
  - Data Selection (table with checkboxes)
  - Target Stage (select: 样本库, 标注任务, 增强任务, etc.)
  - Comments (optional, textarea)
- **API**: `useReview().submitForReview(targetType, targetId)`
- **Validation**: At least one data item selected, target stage required
- **Flexible Flow**: Users can select any target stage, data becomes visible there after approval

#### 4. CreateTaskModal
- **Purpose**: Create annotation task with data source selection
- **Form Fields**:
  - Task Name (required, text input)
  - Description (optional, textarea)
  - Source Stage (select: any stage with data)
  - Data Selection (table with checkboxes)
  - Priority (select: low, medium, high, urgent)
  - Assignee (optional, user select)
  - Due Date (optional, date picker)
- **API**: `useAnnotationTask().createTask()`
- **Validation**: Name required, at least one data item selected
- **Flexible Flow**: Can select data from any stage

#### 5. CreateEnhancementModal
- **Purpose**: Create data enhancement task
- **Form Fields**:
  - Task Name (required, text input)
  - Enhancement Type (select: grammar, style, content, summary, translation, custom)
  - Source Stage (select: any stage)
  - Data Selection (table with checkboxes)
  - Max Iterations (optional, number input)
  - Configuration (optional, JSON editor)
- **API**: `useEnhancement().createJob()`
- **Validation**: Name and type required, at least one data item selected
- **Flexible Flow**: Can select data from any stage

#### 6. CreateTrialModal
- **Purpose**: Create AI trial with flexible stage selection
- **Form Fields**:
  - Trial Name (required, text input)
  - AI Model (select: available models)
  - Data Stage (select: 临时表, 样本库, 数据源, 已标注, 已增强)
  - Data Selection (table with checkboxes, filtered by stage)
  - Trial Count (optional, number input, default: 10)
  - Configuration (optional, JSON editor)
- **API**: `useAITrial().createTrial()`
- **Validation**: Name and model required, at least one data item selected
- **Flexible Flow**: Can select data from any of the 5 stages

### Component Architecture

```
DataLifecycleDashboard
├── QuickActions (modified)
│   ├── State: modalVisibility for each modal
│   ├── Handlers: openModal, closeModal
│   └── Modals:
│       ├── CreateTempDataModal
│       ├── AddToLibraryModal
│       ├── SubmitReviewModal
│       ├── CreateTaskModal
│       ├── CreateEnhancementModal
│       └── CreateTrialModal
```

### Data Flow

```
User clicks button
  → handleAction(key) called
  → setModalVisibility({ [key]: true })
  → Modal component renders with visible=true
  → User fills form
  → User clicks submit
  → Modal calls API via hook
  → On success: close modal, refresh dashboard data, show success message
  → On error: show error message, keep modal open
```

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that clicking buttons only logs to console.

**Test Plan**: Write tests that simulate button clicks and assert that modals should open. Run these tests on the UNFIXED code to observe failures.

**Test Cases**:
1. **Create Temp Data Test**: Click "创建临时数据" button → Assert modal opens (will fail on unfixed code)
2. **Add to Library Test**: Click "添加到样本库" button → Assert modal opens (will fail on unfixed code)
3. **Submit Review Test**: Click "提交审核" button → Assert modal opens (will fail on unfixed code)
4. **Create Task Test**: Click "创建标注任务" button → Assert modal opens (will fail on unfixed code)
5. **Create Enhancement Test**: Click "创建增强任务" button → Assert modal opens (will fail on unfixed code)
6. **Create Trial Test**: Click "创建AI试算" button → Assert modal opens (will fail on unfixed code)

**Expected Counterexamples**:
- Modals do not open when buttons are clicked
- Only console.log output is produced
- No API calls are made

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (clicking quick action buttons), the fixed function opens the correct modal.

**Pseudocode:**
```
FOR ALL actionKey IN ['createTempData', 'addToLibrary', 'submitReview', 
                       'createTask', 'createEnhancement', 'createTrial'] DO
  simulateButtonClick(actionKey)
  ASSERT modalIsVisible(actionKey)
  ASSERT modalHasCorrectFormFields(actionKey)
END FOR
```

**Test Plan**: After implementing the fix, verify each button opens its corresponding modal with correct form fields.

**Test Cases**:
1. **Modal Opening**: Each button click opens the correct modal
2. **Form Fields**: Each modal contains the required form fields
3. **Data Source Selection**: Modals that support flexible flow show stage selection
4. **API Integration**: Form submission calls the correct API method
5. **Success Handling**: Successful submission closes modal and refreshes dashboard
6. **Error Handling**: Failed submission shows error message and keeps modal open
7. **Internationalization**: All text uses translation keys

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (non-quick-action interactions), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL interaction WHERE NOT isQuickActionButtonClick(interaction) DO
  ASSERT originalBehavior(interaction) = fixedBehavior(interaction)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for non-quick-action interactions, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Button Display Preservation**: Verify buttons display correctly with icons, labels, and colors
2. **Hover Effects Preservation**: Verify hover effects continue to work
3. **Tab Navigation Preservation**: Verify tab navigation works correctly
4. **Dashboard Statistics Preservation**: Verify statistics display correctly
5. **Recent Activity Preservation**: Verify recent activity list displays correctly
6. **Permission Checks Preservation**: Verify buttons respect permission checks

### Unit Tests

- Test each modal component renders correctly
- Test form validation for each modal
- Test API integration for each modal
- Test success and error handling
- Test modal open/close state management
- Test internationalization for all text

### Property-Based Tests

- Generate random button click sequences and verify correct modals open
- Generate random form inputs and verify validation works correctly
- Generate random API responses and verify error handling
- Test that all non-quick-action interactions continue to work across many scenarios

### Integration Tests

- Test full flow: click button → fill form → submit → verify dashboard updates
- Test flexible data flow: select data from different stages → verify correct API calls
- Test error scenarios: API failures, validation errors, network errors
- Test concurrent operations: multiple modals, rapid button clicks
- Test internationalization: switch language → verify all text updates
