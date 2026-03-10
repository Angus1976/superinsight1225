# Bugfix Requirements Document

## Introduction

This document addresses the bug where quick action buttons in the data lifecycle management page (localhost:5173/data-lifecycle) are non-functional. When users click any of the 6 quick action buttons (创建临时数据, 添加到样本库, 提交审核, 创建标注任务, 创建增强任务, 创建AI试算), nothing happens except a console log. The buttons should trigger appropriate actions such as opening creation modals or navigating to relevant pages.

**Important Note on Data Flow**: The data lifecycle flow is flexible and non-linear. Users can directly transfer data to any downstream stage without following a strict sequential process. For example:
- Temporary data can be directly added to sample library, or directly submitted for review
- Data can skip intermediate stages and jump to any target stage
- After approval/review, data becomes visible in the selected target stage
- The system should support flexible stage selection in modals rather than enforcing a fixed pipeline

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN user clicks "创建临时数据" (Create Temp Data) button THEN the system only logs to console without opening creation modal

1.2 WHEN user clicks "添加到样本库" (Add to Sample Library) button THEN the system only logs to console without opening selection modal

1.3 WHEN user clicks "提交审核" (Submit for Review) button THEN the system only logs to console without opening review submission modal

1.4 WHEN user clicks "创建标注任务" (Create Annotation Task) button THEN the system only logs to console without opening task creation modal

1.5 WHEN user clicks "创建增强任务" (Create Enhancement Task) button THEN the system only logs to console without opening enhancement creation modal

1.6 WHEN user clicks "创建AI试算" (Create AI Trial) button THEN the system only logs to console without opening AI trial creation modal

### Expected Behavior (Correct)

2.1 WHEN user clicks "创建临时数据" button THEN the system SHALL open a modal to create new temporary data with form fields for data input

2.2 WHEN user clicks "添加到样本库" button THEN the system SHALL open a modal to select data from any stage (临时数据, 已标注, 已增强) and add them to the sample library with optional target stage selection

2.3 WHEN user clicks "提交审核" button THEN the system SHALL open a modal to select data from any stage and submit for review with target stage selection (样本库, 标注任务, 增强任务, etc.)

2.4 WHEN user clicks "创建标注任务" button THEN the system SHALL open a modal to create a new annotation task with data source selection from any available stage

2.5 WHEN user clicks "创建增强任务" button THEN the system SHALL open a modal to create a new enhancement task with data source selection from any available stage

2.6 WHEN user clicks "创建AI试算" button THEN the system SHALL open a modal to create a new AI trial with flexible data stage selection (临时表, 样本库, 数据源, 已标注, 已增强)

2.7 WHEN user submits data for review with a target stage selected THEN the system SHALL make the data visible in the target stage after approval

2.8 WHEN user transfers data between stages THEN the system SHALL NOT enforce a strict sequential flow and SHALL allow direct jumps to any downstream stage

### Unchanged Behavior (Regression Prevention)

3.1 WHEN user navigates to data lifecycle page THEN the system SHALL CONTINUE TO display all 6 quick action buttons with correct icons and labels

3.2 WHEN user hovers over quick action buttons THEN the system SHALL CONTINUE TO show hover effects and visual feedback

3.3 WHEN user clicks on tab navigation (临时数据, 样本库, etc.) THEN the system SHALL CONTINUE TO navigate to corresponding sub-pages correctly

3.4 WHEN user interacts with data tables in sub-pages THEN the system SHALL CONTINUE TO display and manage data correctly

3.5 WHEN user performs actions through sub-page interfaces (not quick actions) THEN the system SHALL CONTINUE TO function as expected
