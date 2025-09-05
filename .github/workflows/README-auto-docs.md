# Auto Documentation Generation Workflow

This GitHub Action automatically generates consistent documentation for new example files using Claude AI's code-reciprocator agent pattern.

## Overview

When a Pull Request is opened with changes to files in the `examples/` directory, this workflow:

1. **Detects Changes**: Identifies new or modified Python example files
2. **Analyzes Patterns**: Studies existing documentation structure and style
3. **Generates Documentation**: Creates consistent docs using Claude AI code-reciprocator pattern
4. **Updates Navigation**: Adds new entries to `mkdocs.yml`
5. **Commits Changes**: Automatically commits documentation to the PR
6. **Adds PR Comment**: Provides summary of generated documentation

## Features

### 🤖 Code-Reciprocator Agent Pattern
- Analyzes existing documentation to understand architectural DNA
- Maintains consistent structure, style, and formatting
- Follows established patterns for integration examples
- Ensures professional quality and technical depth

### 📄 Documentation Generation
- **Consistent Structure**: Same sections across all integration docs
- **Professional Quality**: Technical depth matching existing docs
- **Complete Coverage**: Overview, code, explanations, setup, use cases
- **Framework-Specific**: Tailored content for each integration

### Automatic Integration
- **Navigation Updates**: Adds new docs to mkdocs.yml automatically  
- **PR Integration**: Works seamlessly with GitHub PR workflow
- **Quality Assurance**: Follows established architectural DNA
- **Commit Attribution**: Proper attribution to Claude AI agent

## Workflow Triggers

```yaml
on:
  pull_request:
    paths:
      - 'examples/**/*.py'
      - 'examples/**/*.md'
    types: [opened, synchronize, reopened]
```

**Triggers on:**
- New Pull Requests with example changes
- Updates to existing PRs with example modifications
- Reopened PRs containing example files

## Requirements

### Repository Secrets
The workflow requires the following secret to be configured in GitHub repository settings:

- `ANTHROPIC_API_KEY`: Your Anthropic Claude API key for documentation generation

### File Structure
The workflow expects this directory structure:
```
examples/
├── integrations/
│   ├── framework_example.py
│   └── another_example.py
└── other_example.py

docs/
└── examples/
    ├── framework-integration.md
    └── other-integration.md
```

## Generated Documentation Structure

Each generated documentation file follows this consistent pattern:

```markdown
# Framework Integration

Memory-enhanced [Framework](link) with persistent conversation memory...

## Overview
- Integration benefits and use cases

## Code  
- Complete example code with syntax highlighting

## What Happens
- Technical breakdown of integration points

## Expected Output
- Sample interactions and responses

## Database Contents
- Memory storage examples

## Setup and Configuration
- Step-by-step installation guide

## Use Cases
- Real-world applications

## Advanced Features
- Extended functionality options

## Best Practices
- Professional implementation guidelines

## Next Steps
- Links to related documentation
```

## Code-Reciprocator Pattern

The workflow uses Claude AI's code-reciprocator agent pattern with this system prompt:

> You are a code-reciprocator agent. Your role is to analyze existing code patterns and create consistent, similar documentation following established patterns and architectural DNA.

This ensures:
- **Pattern Recognition**: Understands existing documentation style
- **Consistency**: Maintains same structure across all docs
- **Quality**: Professional technical writing standards
- **Architectural DNA**: Preserves established patterns

## Workflow Steps

### 1. Change Detection
```bash
git diff --name-only origin/$BASE_BRANCH...HEAD -- examples/
```

### 2. Pattern Analysis
- Reads existing documentation files
- Extracts structural patterns and style
- Prepares samples for Claude AI analysis

### 3. Documentation Generation
- Sends example code and patterns to Claude AI
- Uses code-reciprocator agent system prompt
- Generates consistent, professional documentation

### 4. Navigation Update
- Parses `mkdocs.yml` configuration
- Adds new documentation entries to Examples section
- Maintains proper YAML formatting

### 5. Git Operations
- Commits generated documentation
- Pushes changes to PR branch
- Adds informative PR comment

## Example Output

When the workflow runs successfully, you'll see:

### PR Comment
```
🤖 Auto-Generated Documentation

I've automatically generated documentation for the new/updated example files...

📄 Processed Files:
- examples/integrations/newframework_example.py

✅ Generated Documentation:
- Created new integration documentation following existing patterns
- Updated mkdocs.yml navigation to include new examples
- Maintained architectural DNA and consistent formatting
```

### Commit Message
```
🤖 Auto-generate documentation for example changes

- Generated consistent documentation following code-reciprocator pattern
- Updated mkdocs.yml navigation with new integration examples  
- Maintained architectural DNA across all integration docs

Generated with Claude AI Code-Reciprocator Agent

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Configuration

The workflow can be customized by modifying these aspects:

### File Patterns
```yaml
paths:
  - 'examples/**/*.py'     # Python example files
  - 'examples/**/*.md'     # Markdown documentation
```

### Claude AI Settings
```python
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=8000,
    temperature=0.1,  # Low temperature for consistency
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}]
)
```

### Framework Detection
```python
def get_framework_name(file_path):
    if 'integrations/' in file_path:
        filename = Path(file_path).stem
        return filename.replace('_example', '')
    else:
        filename = Path(file_path).stem
        return filename.replace('_', '-')
```

## Troubleshooting

### Common Issues

1. **Missing API Key**
   ```
   Error: ANTHROPIC_API_KEY not found
   ```
   **Solution**: Add the secret in GitHub repository settings

2. **Git Push Failures**
   ```
   Error: Permission denied (publickey)
   ```
   **Solution**: Ensure workflow has write permissions

3. **Documentation Generation Fails**
   ```
   Error generating documentation: API limit exceeded
   ```
   **Solution**: Check Anthropic API usage and limits

### Debug Information

The workflow provides detailed logging:
- Changed files detection
- Documentation generation progress  
- Git operations status
- Error messages with context

## Integration with CI/CD

This workflow integrates with your existing CI/CD pipeline:

1. **Runs on PR Events**: Doesn't block main branch
2. **Documentation Preview**: Works with docs preview workflows
3. **Quality Checks**: Generated docs can be validated by other workflows
4. **Auto-Deployment**: Documentation deploys with regular docs build

## Best Practices

### Example File Guidelines
- Use clear, descriptive filenames
- Follow naming convention: `framework_example.py`
- Include comprehensive docstrings
- Add setup instructions in comments

### Documentation Quality
- The code-reciprocator agent ensures consistency
- Generated docs follow established patterns
- Manual review recommended for complex integrations
- Framework-specific details are automatically included

## Future Enhancements

Potential improvements to consider:

1. **Multi-Language Support**: Generate docs for non-Python examples
2. **Custom Templates**: Framework-specific documentation templates
3. **Validation**: Automated testing of generated code examples
4. **Localization**: Multi-language documentation generation
5. **Analytics**: Track documentation usage and effectiveness

---

*This workflow is powered by Claude AI's code-reciprocator agent pattern for consistent, high-quality documentation generation.*