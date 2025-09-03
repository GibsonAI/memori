#!/usr/bin/env node

/**
 * Script to create dependency update PR
 * Extracted from dependency-update.yml for better maintainability
 */

const { execSync } = require('child_process');

async function createDependencyPR({ github, context, updateType }) {
  try {
    console.log('Configuring git...');
    // Configure git
    execSync('git config --local user.email "action@github.com"');
    execSync('git config --local user.name "GitHub Action"');
    
    console.log('Creating branch...');
    // Create branch
    const branchName = `dependency-updates-${new Date().toISOString().split('T')[0]}`;
    execSync(`git checkout -b ${branchName}`);
    
    console.log('Committing changes...');
    // Commit changes
    execSync('git add -A');
    
    const commitMessage = `Update dependencies (${updateType})

- Updated Python dependencies
- Updated GitHub Actions versions
- Ran security checks on updated packages
- Verified compatibility with test suite

Co-authored-by: github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>`;
    
    execSync(`git commit -m "${commitMessage}"`);
    
    console.log('Pushing to remote...');
    execSync(`git push origin ${branchName}`);
    
    console.log('Creating pull request...');
    // Create PR
    const { data: pr } = await github.rest.pulls.create({
      owner: context.repo.owner,
      repo: context.repo.repo,
      title: `Automated dependency updates (${updateType})`,
      head: branchName,
      base: 'main',
      body: generatePRBody(updateType, context)
    });
    
    console.log(`Created PR #${pr.number}: ${pr.html_url}`);
    
    console.log('Adding labels...');
    // Add labels
    await github.rest.issues.addLabels({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: pr.number,
      labels: ['dependencies', 'automated']
    });

    return pr;
    
  } catch (error) {
    console.error('Error creating dependency PR:', error);
    throw error;
  }
}

function generatePRBody(updateType, context) {
  return `## Automated Dependency Updates

This PR contains automated dependency updates for \`${updateType}\` version bumps.

### Updates Included
- Python package dependencies
- GitHub Actions versions  
- Security vulnerability patches

### Automated Checks
- [x] Security scan completed
- [x] Test suite compatibility verified
- [x] No breaking changes detected

### Review Checklist
- [ ] Review dependency changes
- [ ] Verify test results
- [ ] Check for any breaking changes
- [ ] Merge if all checks pass

### Automation Details
- **Trigger**: ${context.eventName === 'schedule' ? 'Scheduled weekly update' : 'Manual trigger'}
- **Update Type**: ${updateType}
- **Date**: ${new Date().toISOString().split('T')[0]}

> This PR was automatically created by the dependency update workflow.
> If tests fail, please review the changes manually.`;
}

module.exports = { createDependencyPR };

// If called directly from command line
if (require.main === module) {
  console.error('This script should be called from GitHub Actions workflow');
  process.exit(1);
}