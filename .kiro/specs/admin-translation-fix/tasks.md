# Admin Console Translation Fix - Tasks

## Task Breakdown

- [x] 1. Analyze and identify duplicate keys (Est: 0.5h)
  - [x] 1.1 Read complete zh/admin.json file (Est: 0.1h)
  - [x] 1.2 Read complete en/admin.json file (Est: 0.1h)
  - [x] 1.3 Identify duplicate keys in zh file (Est: 0.2h)
  - [x] 1.4 Identify duplicate keys in en file (Est: 0.1h)
  - **Validates**: Requirements 4.1

- [x] 2. Fix duplicate keys in Chinese translation file (Est: 1h)
  - [x] 2.1 Extract and compare duplicate `permissionConfig` sections (Est: 0.2h)
  - [x] 2.2 Merge unique content from `permissionConfig` duplicates (Est: 0.2h)
  - [x] 2.3 Remove duplicate `permissionConfig` section (Est: 0.1h)
  - [x] 2.4 Check and fix any other duplicate keys (Est: 0.3h)
  - [x] 2.5 Validate JSON syntax (Est: 0.1h)
  - [x] 2.6 Verify file structure (Est: 0.1h)
  - **Validates**: Requirements 4.1, 4.3

- [x] 3. Fix duplicate keys in English translation file (Est: 1h)
  - [x] 3.1 Extract and compare duplicate `permissionConfig` sections (Est: 0.2h)
  - [x] 3.2 Merge unique content from `permissionConfig` duplicates (Est: 0.2h)
  - [x] 3.3 Remove duplicate `permissionConfig` section (Est: 0.1h)
  - [x] 3.4 Check and fix any other duplicate keys (Est: 0.3h)
  - [x] 3.5 Validate JSON syntax (Est: 0.1h)
  - [x] 3.6 Verify file structure matches zh file (Est: 0.1h)
  - **Validates**: Requirements 4.1, 4.3

- [x] 4. Rebuild and restart frontend container (Est: 0.3h)
  - [x] 4.1 Rebuild frontend Docker image (Est: 0.2h)
  - [x] 4.2 Restart frontend container (Est: 0.1h)
  - **Validates**: Requirements 6.2

- [x] 5. Test admin console pages (Est: 0.5h)
  - [x] 5.1 Clear browser cache (Est: 0.05h)
  - [x] 5.2 Test Console/Overview page translations (Est: 0.1h)
  - [x] 5.3 Test Billing Management page translations (Est: 0.1h)
  - [x] 5.4 Test Permission Config page translations (Est: 0.1h)
  - [x] 5.5 Test Quota Management page translations (Est: 0.1h)
  - [x] 5.6 Test language switching (zh ↔ en) (Est: 0.05h)
  - **Validates**: Requirements 6.2, 6.3

- [x] 6. Verify no translation issues remain (Est: 0.2h)
  - [x] 6.1 Check browser console for i18n warnings (Est: 0.1h)
  - [x] 6.2 Verify no raw translation keys visible (Est: 0.1h)
  - **Validates**: Requirements 6.2, 6.3

## Progress Tracking
- Total Tasks: 6
- Completed: 0
- In Progress: 0
- Blocked: 0

## Estimated Total Time
3.5 hours

## Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 1
- Task 4 depends on Tasks 2 and 3
- Task 5 depends on Task 4
- Task 6 depends on Task 5

## Notes
- Keep backup of original files before modification
- Test thoroughly after each fix
- Document any unexpected issues found
