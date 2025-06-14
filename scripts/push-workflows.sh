#!/bin/bash
# Script to push workflow changes with proper authentication

echo "=== TINAA Workflow Push Script ==="
echo
echo "This script will help you push the workflow fixes to GitHub."
echo "You need a token with 'workflow' scope."
echo

# Check if we're on the right branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "fix/ci-workflows" ]; then
    echo "Switching to fix/ci-workflows branch..."
    git checkout fix/ci-workflows
fi

echo "Choose authentication method:"
echo "1. GitHub Personal Access Token (recommended)"
echo "2. GitHub CLI with browser auth"
echo "3. Exit"
echo
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo
        echo "Create a token at: https://github.com/settings/tokens/new"
        echo "Required scopes: repo (all), workflow"
        echo
        read -s -p "Enter your Personal Access Token: " token
        echo
        echo "Pushing to GitHub..."
        git push https://$token@github.com/aj-geddes/tinaa-playwright-msp.git fix/ci-workflows
        ;;
    2)
        echo
        echo "Logging in with GitHub CLI..."
        gh auth login -h github.com -p https -s repo,workflow -w
        echo "Pushing to GitHub..."
        git push origin fix/ci-workflows
        ;;
    3)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    echo
    echo "✅ Successfully pushed workflow fixes!"
    echo
    echo "Next steps:"
    echo "1. Go to: https://github.com/aj-geddes/tinaa-playwright-msp/pulls"
    echo "2. Create a pull request from 'fix/ci-workflows' to 'main'"
    echo "3. Merge the PR to apply the fixes"
else
    echo
    echo "❌ Push failed. Please check your authentication and try again."
fi