# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Missing Imports Cause Compilation Errors
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope the property to the concrete failing case(s) to ensure reproducibility
  - Test that TypeScript compilation fails with specific errors:
    - Error 1: "找不到名称'ExclamationCircleOutlined'" at line 614
    - Error 2: "类型'LearningProgress'上不存在属性'error_message'" at lines 523, 526
    - Error 3: "类型'BatchProgress'上不存在属性'error_message'" at lines 631, 634
  - Run TypeScript compiler on UNFIXED file: `npx tsc --noEmit frontend/src/pages/AIProcessing/AIAnnotationWorkflowContent.tsx`
  - **EXPECTED OUTCOME**: Compilation FAILS with 3 distinct error types (this is correct - it proves the bug exists)
  - Document counterexamples found to understand root cause
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Functionality Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (code that doesn't involve ExclamationCircleOutlined or error_message)
  - Write tests capturing observed behavior patterns:
    - Test 1: All existing imports (DatabaseOutlined, RobotOutlined, CheckCircleOutlined, etc.) compile successfully
    - Test 2: Component renders successfully in normal (non-error) states
    - Test 3: All existing UI elements (Card, Steps, Button, Typography, progress bars) render correctly
    - Test 4: State management and workflow transitions work correctly
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix for missing imports in AI annotation workflow component

  - [x] 3.1 Add missing ExclamationCircleOutlined import
    - Locate the import block from `@ant-design/icons` (lines 24-30)
    - Add `ExclamationCircleOutlined` to the list of imported icons
    - Maintain alphabetical ordering for consistency
    - _Bug_Condition: isBugCondition(input) where input.type == 'compilation' AND fileContains('ExclamationCircleOutlined') AND NOT importContains('ExclamationCircleOutlined')_
    - _Expected_Behavior: TypeScript compilation succeeds without "找不到名称'ExclamationCircleOutlined'" error_
    - _Preservation: All existing icon imports and usage remain unchanged_
    - _Requirements: 2.1, 2.4_

  - [x] 3.2 Add error_message property to LearningProgress interface
    - Locate the LearningProgress interface definition (around line 60)
    - Add `error_message?: string;` as an optional property
    - Place it logically after the `status` property
    - _Bug_Condition: isBugCondition(input) where input.type == 'compilation' AND codeAccesses('learningProgress.error_message') AND NOT interfaceDefines('LearningProgress', 'error_message')_
    - _Expected_Behavior: TypeScript compilation succeeds without "类型'LearningProgress'上不存在属性'error_message'" error_
    - _Preservation: All existing LearningProgress properties and usage remain unchanged_
    - _Requirements: 2.2, 2.5_

  - [x] 3.3 Add error_message property to BatchProgress interface
    - Locate the BatchProgress interface definition (around line 70)
    - Add `error_message?: string;` as an optional property
    - Place it logically after the `status` property
    - _Bug_Condition: isBugCondition(input) where input.type == 'compilation' AND codeAccesses('batchProgress.error_message') AND NOT interfaceDefines('BatchProgress', 'error_message')_
    - _Expected_Behavior: TypeScript compilation succeeds without "类型'BatchProgress'上不存在属性'error_message'" error_
    - _Preservation: All existing BatchProgress properties and usage remain unchanged_
    - _Requirements: 2.3, 2.5_

  - [x] 3.4 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Missing Imports Resolved
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run TypeScript compiler: `npx tsc --noEmit frontend/src/pages/AIProcessing/AIAnnotationWorkflowContent.tsx`
    - **EXPECTED OUTCOME**: Compilation PASSES with no errors (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.5 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Functionality Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Checkpoint - Ensure all tests pass
  - Verify TypeScript compilation succeeds with no errors
  - Verify all preservation tests pass
  - Verify component renders correctly in both normal and error states
  - Ask the user if questions arise
