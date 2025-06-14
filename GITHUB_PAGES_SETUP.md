# GitHub Pages Setup Guide for TINAA Documentation

Follow these steps to enable GitHub Pages for your TINAA documentation:

## 📋 Prerequisites

- Repository pushed to GitHub ✅
- MkDocs documentation ready ✅
- GitHub Actions workflow configured ✅

## 🚀 Setup Steps

### 1. Enable GitHub Pages in Repository Settings

1. Go to your repository: https://github.com/aj-geddes/tinaa-playwright-msp
2. Click on **Settings** (top menu)
3. Scroll down to **Pages** in the left sidebar

### 2. Configure GitHub Pages Source

In the Pages settings:

1. **Source**: Select `GitHub Actions` (not "Deploy from a branch")
   - This uses our MkDocs workflow to build and deploy

### 3. Configure Custom Domain (Optional)

If you have a custom domain:
1. Enter your domain in the "Custom domain" field
2. Click "Save"
3. Enable "Enforce HTTPS"

### 4. Trigger the Documentation Build

The documentation will build automatically on the next push to main. To trigger it now:

```bash
# Option 1: Make a small change
echo "# Trigger docs build $(date)" >> docs/tags.md
git add docs/tags.md
git commit -m "docs: Trigger GitHub Pages build"
git push origin main

# Option 2: Manually trigger the workflow
# Go to Actions tab → Deploy MkDocs Documentation → Run workflow
```

## 5. Access Your Documentation

After the workflow completes (usually 2-3 minutes):

- **GitHub Pages URL**: https://aj-geddes.github.io/tinaa-playwright-msp/
- **Check deployment**: Go to Settings → Pages to see the live URL

## 🔍 Verification Steps

1. Check the Actions tab for successful workflow run
2. Look for the green checkmark on "Deploy MkDocs Documentation"
3. Click on the workflow run to see deployment details
4. Visit your GitHub Pages URL

## 🛠️ Troubleshooting

### If the site doesn't appear:

1. **Check workflow permissions**:
   - Settings → Actions → General
   - Workflow permissions: Select "Read and write permissions"
   - Check "Allow GitHub Actions to create and approve pull requests"

2. **Check Pages settings**:
   - Ensure "Source" is set to "GitHub Actions"
   - Check if there's a custom domain conflict

3. **Check workflow status**:
   - Go to Actions tab
   - Look for any failed workflows
   - Check the logs for errors

### Common Issues:

- **404 Error**: Wait a few minutes for DNS propagation
- **Build Failures**: Check if all MkDocs dependencies are in requirements-mkdocs.txt
- **Permission Errors**: Enable GitHub Actions permissions in repository settings

## 📝 Notes

- First deployment may take up to 10 minutes
- Subsequent deployments are usually faster (2-3 minutes)
- The site is automatically rebuilt on every push to main
- You can also manually trigger builds from the Actions tab

## 🎉 Success!

Once configured, your documentation will be available at:
- https://aj-geddes.github.io/tinaa-playwright-msp/

The site will automatically update whenever you push changes to the main branch!