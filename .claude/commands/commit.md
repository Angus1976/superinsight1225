# Create Atomic Commit

Create a well-formatted atomic commit for all uncommitted changes.

## Process

### 1. Check Current Status

```bash
git status
```

Review what files have been changed, added, or deleted.

### 2. Review Changes

```bash
git diff HEAD
```

Review the actual code changes to understand what was modified.

### 3. Stage Files

```bash
# Stage all changes
git add .

# Or stage specific files
git add <file1> <file2>
```

### 4. Create Commit Message

Follow the Conventional Commits specification:

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature change or bug fix)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Build process, dependencies, tooling
- `ci`: CI/CD configuration changes
- `revert`: Revert a previous commit

**Scope (optional):**
- `api`: Backend API changes
- `ui`: Frontend UI changes
- `db`: Database changes
- `auth`: Authentication/authorization
- `i18n`: Internationalization
- `docker`: Docker configuration
- etc.

**Examples:**

```bash
# Feature
git commit -m "feat(api): add user profile endpoint

- Add GET /api/users/{id}/profile endpoint
- Add ProfileSchema for request/response
- Add unit tests for profile API
- Update API documentation

Closes #123"

# Bug fix
git commit -m "fix(ui): resolve dashboard loading hang issue

- Increase API timeout from 1s to 10s
- Add loading state indicator
- Fix useDashboard hook context handling

Fixes #456"

# Documentation
git commit -m "docs: add PIV methodology integration guide

- Add PIV quick start guide
- Add Claude commands setup documentation
- Update CLAUDE.md with project-specific configuration"

# Refactor
git commit -m "refactor(hooks): fix TypeScript export naming

- Rename useTaskList to useTasks
- Rename useHover to useHoverState
- Remove non-existent exports
- Add TypeScript export rules documentation"

# Chore
git commit -m "chore(deps): update frontend dependencies

- Update React to 19.x
- Update Vite to 7.x
- Update Ant Design to 5.x"
```

### 5. Commit

```bash
git commit -m "<your-commit-message>"
```

### 6. Verify Commit

```bash
# View the commit
git log -1

# View the commit with changes
git show HEAD
```

## Best Practices

1. **Atomic Commits**: Each commit should represent one logical change
2. **Clear Subject**: Keep subject line under 50 characters
3. **Descriptive Body**: Explain what and why, not how
4. **Reference Issues**: Use "Closes #123" or "Fixes #456"
5. **Test Before Commit**: Run `/validation:validate` before committing
6. **Sign Commits**: Use `git commit -s` to sign commits (if required)

## Commit Message Template

```
<type>(<scope>): <subject line - imperative mood, max 50 chars>

<body - wrap at 72 characters>
- What was changed
- Why it was changed
- Any side effects or considerations

<footer>
Closes #<issue-number>
Breaking Change: <description if applicable>
```

## Notes

- Use imperative mood in subject line ("add" not "added" or "adds")
- Capitalize the subject line
- No period at the end of subject line
- Separate subject from body with a blank line
- Wrap body at 72 characters
- Use body to explain what and why vs. how
