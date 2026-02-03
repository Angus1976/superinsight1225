# Kiro Hooks

## Active Hooks

### On Save (fileEdited)

#### 1. on-save-quality-check.kiro.hook
**Triggers**: `**/*.py`, `**/*.ts`, `**/*.tsx`, `**/*.js`, `**/*.jsx`  
**Purpose**: Runs linters, formatters, and tests on file save  
**Actions**:
- Test files: Runs specific test
- Python files: `black` + `isort` + `ruff check`
- TypeScript files: `prettier` + `eslint`

#### 2. doc-first-enforcer.kiro.hook
**Triggers**: `src/**/*.py`, `frontend/src/**/*.tsx`, `frontend/src/**/*.ts`  
**Purpose**: Reminds about doc-first workflow  
**Actions**: Brief reminder to update requirements.md, design.md, tasks.md, CHANGELOG.md

#### 3. typescript-quality-check.kiro.hook
**Triggers**: `frontend/src/**/*.ts`, `frontend/src/**/*.tsx`  
**Purpose**: TypeScript-specific quality checks  
**Actions**:
- index.ts: Verify exports exist, check duplicates
- API services: Verify generic types on api.get/post/put/delete
- All TS: Run `tsc --noEmit`

#### 4. hook-naming-check.kiro.hook
**Triggers**: `frontend/src/hooks/*.ts`  
**Purpose**: Ensures React hook naming conventions  
**Actions**: Checks for `use` prefix, plural forms, State suffix

### On Commit (promptSubmit)
None currently

### On Demand (userTriggered)
None currently

## Configuration

### Auto-Approval
Auto-approval is handled by **Kiro's Trusted Commands** (Settings > Trusted Commands).

**Recommended Trusted Commands**:
```
python, pytest, npm, npx, pip, git, docker, docker-compose, alembic
black, isort, prettier, eslint, vitest
cat, ls, head, tail, grep, find, cd, pwd, mkdir, touch, echo
```

### Steering Rules
See `.kiro/steering/` for development guidelines:
- `product.md` - Product context
- `structure.md` - Project structure
- `tech.md` - Tech stack
- `typescript-export-rules.md` - TypeScript guidance
- `i18n-translation-rules.md` - i18n guidance
- `file-organization-rules.md` - File organization
- `documentation-minimalism-rules.md` - Doc standards
- `async-sync-safety-quick-reference.md` - Async safety (always loaded)
- `async-sync-safety.md` - Full async rules (manual load)
- `auto-approve-guide.md` - Auto-approval reference

## Hook Development Guidelines

### Naming Convention
- `on-save-*` - fileEdited trigger
- `on-commit-*` - promptSubmit trigger
- `on-demand-*` - userTriggered trigger

### Best Practices
1. **Be concise** - Brief prompts, clear actions
2. **Report errors only** - No success messages
3. **One purpose per hook** - Avoid overlapping responsibilities
4. **Trust the developer** - Reminders, not enforcement
5. **Use Trusted Commands** - Don't implement auto-approval in hooks

## Maintenance

### Adding a New Hook
1. Follow naming convention
2. Define clear trigger patterns
3. Write concise prompt
4. Test with actual file saves
5. Update this README

### Disabling a Hook
Set `"enabled": false` in the hook file.

### Debugging Hooks
Check Kiro's output panel for hook execution logs.

## Migration Notes

**2026-02-03**: Consolidated from 12 hooks to 4 hooks
- Removed legacy auto-approval hooks (use Trusted Commands)
- Consolidated file-save actions into one hook
- Simplified documentation hooks (5 → 1)
- Consolidated TypeScript hooks (3 → 1)
- **Token savings**: ~10,000 tokens per session
