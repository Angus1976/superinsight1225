# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Quick Action Buttons Do Not Open Modals
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to the 6 concrete failing cases (button clicks)
  - Test that clicking each of the 6 quick action buttons opens the corresponding modal
  - Test cases: ['createTempData', 'addToLibrary', 'submitReview', 'createTask', 'createEnhancement', 'createTrial']
  - For each button: simulate click → assert modal opens with correct form fields
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found (e.g., "clicking 'createTempData' button does not open CreateTempDataModal")
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Quick-Action Interactions Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-quick-action interactions:
    - Button display with icons, labels, and colors
    - Hover effects and visual feedback
    - Tab navigation between lifecycle stages
    - Dashboard statistics display
    - Recent activity display
  - Write property-based tests capturing observed behavior patterns:
    - Test 1: All 6 buttons render with correct icons, labels, and colors
    - Test 2: Hover effects work on all buttons
    - Test 3: Tab navigation works correctly for all tabs
    - Test 4: Dashboard statistics display correctly
    - Test 5: Recent activity list displays correctly
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Implement quick action modal functionality

  - [x] 3.1 Create modal state management in QuickActions component
    - Add state variables to control visibility of each modal
    - Add handler functions to open/close modals
    - Update handleAction function to open correct modal based on action key
    - _Bug_Condition: isBugCondition(input) where input.actionKey IN ['createTempData', 'addToLibrary', 'submitReview', 'createTask', 'createEnhancement', 'createTrial'] AND input.userClick === true_
    - _Expected_Behavior: Modal opens with appropriate form fields and data source selection options_
    - _Preservation: Button display, hover effects, tab navigation remain unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3_

  - [x] 3.2 Create CreateTempDataModal component
    - Form fields: Name (required), Content (required, JSON editor), Metadata (optional)
    - Integrate with useTempData().createTempData() API
    - Add form validation: Name required, content must be valid JSON
    - Add internationalization using t() for all text
    - Handle success: close modal, refresh dashboard, show success message
    - Handle errors: show error message, keep modal open
    - _Requirements: 2.1_

  - [x] 3.3 Create AddToLibraryModal component
    - Form fields: Source Stage (select), Data Selection (table with checkboxes), Description (optional), Data Type (select)
    - Support flexible data flow: allow selection from any stage (临时数据, 已标注, 已增强)
    - Integrate with useSampleLibrary().addToLibrary() API
    - Add form validation: At least one data item selected
    - Add internationalization using t() for all text
    - Handle success: close modal, refresh dashboard, show success message
    - Handle errors: show error message, keep modal open
    - _Requirements: 2.2, 2.8_

  - [x] 3.4 Create SubmitReviewModal component
    - Form fields: Source Stage (select), Data Selection (table), Target Stage (select), Comments (optional)
    - Support flexible data flow: allow selection from any stage and any target stage
    - Integrate with useReview().submitForReview() API
    - Add form validation: At least one data item selected, target stage required
    - Add internationalization using t() for all text
    - Handle success: close modal, refresh dashboard, show success message
    - Handle errors: show error message, keep modal open
    - _Requirements: 2.3, 2.7, 2.8_

  - [x] 3.5 Create CreateTaskModal component
    - Form fields: Task Name (required), Description, Source Stage (select), Data Selection (table), Priority (select), Assignee, Due Date
    - Support flexible data flow: allow data selection from any stage
    - Integrate with useAnnotationTask().createTask() API
    - Add form validation: Name required, at least one data item selected
    - Add internationalization using t() for all text
    - Handle success: close modal, refresh dashboard, show success message
    - Handle errors: show error message, keep modal open
    - _Requirements: 2.4, 2.8_

  - [x] 3.6 Create CreateEnhancementModal component
    - Form fields: Task Name (required), Enhancement Type (select), Source Stage (select), Data Selection (table), Max Iterations, Configuration (JSON)
    - Support flexible data flow: allow data selection from any stage
    - Integrate with useEnhancement().createJob() API
    - Add form validation: Name and type required, at least one data item selected
    - Add internationalization using t() for all text
    - Handle success: close modal, refresh dashboard, show success message
    - Handle errors: show error message, keep modal open
    - _Requirements: 2.5, 2.8_

  - [x] 3.7 Create CreateTrialModal component
    - Form fields: Trial Name (required), AI Model (select), Data Stage (select: 临时表, 样本库, 数据源, 已标注, 已增强), Data Selection (table), Trial Count, Configuration (JSON)
    - Support flexible data flow: allow data selection from any of the 5 stages
    - Integrate with useAITrial().createTrial() API
    - Add form validation: Name and model required, at least one data item selected
    - Add internationalization using t() for all text
    - Handle success: close modal, refresh dashboard, show success message
    - Handle errors: show error message, keep modal open
    - _Requirements: 2.6, 2.8_

  - [x] 3.8 Add internationalization support
    - Verify all modal titles, labels, placeholders, and messages use t() function
    - Verify translation keys exist in frontend/src/locales/zh/dataLifecycle.json
    - Verify translation keys exist in frontend/src/locales/en/dataLifecycle.json
    - Add any missing translation keys
    - Test language switching works correctly
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 3.9 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Quick Action Buttons Open Modals
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - Verify all 6 button clicks now open correct modals
    - Verify modals contain correct form fields
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 3.10 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Quick-Action Interactions Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm button display, hover effects, tab navigation still work correctly
    - Confirm dashboard statistics and recent activity display correctly
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run all tests (bug condition + preservation)
  - Verify all 6 quick action buttons open correct modals
  - Verify all modals have correct form fields and validation
  - Verify flexible data flow works (stage selection)
  - Verify API integration works correctly
  - Verify internationalization works correctly
  - Verify no regressions in existing functionality
  - Ask the user if questions arise
