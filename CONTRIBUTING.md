# Contributing to LexiqAI

Thank you for your interest in contributing to LexiqAI! This document provides guidelines and instructions for contributing.

## Development Workflow

### 1. Branch Strategy

- **`main`** - Production-ready code
- **`develop`** - Integration branch for features
- **Feature branches** - `feature/description` or `feature/issue-number`
- **Bug fixes** - `fix/description` or `fix/issue-number`
- **Infrastructure** - `infra/description`

### 2. Creating a Branch

```bash
# Create and switch to a new feature branch
git checkout -b feature/my-feature

# Or from develop
git checkout develop
git pull origin develop
git checkout -b feature/my-feature
```

### 3. Making Changes

- Write clear, self-documenting code
- Follow existing code style and patterns
- Add comments for complex logic
- Update documentation as needed
- Write or update tests

### 4. Commit Messages

Follow conventional commit format:

```
type(scope): brief description

Longer explanation if needed
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `infra`: Infrastructure changes

**Examples:**
```
feat(voice-gateway): add Twilio WebSocket connection handler
fix(api-core): resolve authentication token validation issue
docs(foundation): update Terraform setup guide
infra(terraform): add Redis cache module
```

### 5. Testing

Before submitting a PR:

- [ ] Run existing tests: `make test`
- [ ] Test in local environment
- [ ] Verify no linting errors: `make lint`
- [ ] For infrastructure changes: Run `terraform validate` and `terraform plan`

### 6. Pull Request Process

1. **Push your branch**
   ```bash
   git push origin feature/my-feature
   ```

2. **Create a Pull Request**
   - Use the PR template
   - Link related issues
   - Request review from team members
   - Ensure CI checks pass

3. **Address Review Feedback**
   - Make requested changes
   - Push updates to the same branch
   - Respond to comments

4. **Merge**
   - PRs require at least one approval
   - Squash and merge (preferred) or rebase and merge
   - Delete the feature branch after merge

## Code Style Guidelines

### Python

- Follow PEP 8 style guide
- Use type hints where possible
- Maximum line length: 100 characters
- Use `black` for formatting (when configured)
- Use meaningful variable and function names

### Go

- Follow [Effective Go](https://go.dev/doc/effective_go) guidelines
- Use `gofmt` for formatting
- Keep functions focused and small
- Document exported functions

### TypeScript/JavaScript

- Follow ESLint configuration
- Use TypeScript for type safety
- Follow Next.js conventions
- Use meaningful component and function names

### Terraform

- Use `terraform fmt` to format files
- Follow module structure conventions
- Document variables and outputs
- Use meaningful resource names

## Project Structure

See [System Design](/docs/design/system-design.md) for complete architecture overview.

### Key Directories

- **`apps/`** - Deployable microservices
- **`libs/`** - Shared libraries
- **`infra/`** - Infrastructure as Code
- **`docs/`** - Documentation
- **`tools/`** - Development scripts

## Infrastructure Changes

For Terraform changes:

1. **Plan First**
   ```bash
   cd infra/terraform
   terraform plan -var-file=dev.tfvars
   ```

2. **Review the Plan**
   - Verify resources to be created/modified/destroyed
   - Check for any unintended changes

3. **Test in Dev**
   - Apply to dev environment first
   - Verify resources work as expected

4. **Document Changes**
   - Update relevant documentation
   - Note any breaking changes
   - Update variable files if needed

## Security Considerations

- **Never commit secrets** - Use environment variables or Azure Key Vault
- **Review authentication changes** - Security-sensitive code requires extra scrutiny
- **Follow principle of least privilege** - Grant minimum required permissions
- **Keep dependencies updated** - Regularly update and audit dependencies

## Getting Help

- Check existing documentation in `/docs`
- Review existing code for patterns
- Ask questions in PR comments or team channels
- Open an issue for bugs or feature requests

## Code Review Guidelines

### For Authors

- Keep PRs focused and reasonably sized
- Provide context in PR description
- Respond to feedback promptly
- Be open to suggestions

### For Reviewers

- Be constructive and respectful
- Focus on code quality and correctness
- Approve when satisfied, or request changes with clear feedback
- Review within 24-48 hours when possible

## Questions?

If you have questions about contributing, please:
1. Check the documentation
2. Review existing issues and PRs
3. Open a discussion or issue

Thank you for contributing to LexiqAI! 🚀

