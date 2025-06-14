# Getting Started with TINAA

Welcome to TINAA! This guide will help you create your first AI-generated test.

## Prerequisites

Before you begin, ensure you have:
- TINAA installed ([Installation Guide](installation.md))
- A web application to test
- Basic knowledge of testing concepts

## Your First Test

### Step 1: Initialize TINAA

```bash
tinaa init
```

### Step 2: Generate a Test

```bash
tinaa generate --url https://your-app.com --prompt "Test the login functionality"
```

### Step 3: Run the Test

```bash
tinaa run tests/generated/login-test.spec.js
```

## Understanding Generated Tests

TINAA generates Playwright-based tests with:
- Intelligent element selection
- Automatic wait strategies
- Built-in error handling
- Comprehensive assertions

## Next Steps

- [Test Generation Guide](test-generation.md)
- [Best Practices](best-practices.md)
- [User Guide](../USER_GUIDE.md)

## Getting Help

- [FAQ](../support/faq.md)
- [Community Support](../support/community.md)
- [Troubleshooting](../TROUBLESHOOTING.md)