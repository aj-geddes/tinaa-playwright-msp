# Custom Resources Development Guide

Learn how to create custom resources, patterns, and extensions for TINAA to support your specific testing needs.

## Overview

Custom resources in TINAA allow you to:
- Define domain-specific test patterns
- Create reusable test components
- Implement custom assertions
- Add specialized test generators

## Custom Test Patterns

### Creating a Pattern

```javascript
// patterns/ecommerce-checkout.js
module.exports = {
  name: 'ecommerce-checkout',
  description: 'E-commerce checkout flow testing pattern',
  
  generate: async (context) => {
    return {
      steps: [
        { action: 'navigate', target: context.url },
        { action: 'addToCart', products: context.products },
        { action: 'proceedToCheckout' },
        { action: 'fillShipping', data: context.shippingData },
        { action: 'fillPayment', data: context.paymentData },
        { action: 'confirmOrder' },
        { action: 'verifyConfirmation' }
      ]
    };
  },
  
  validators: {
    cartTotal: (expected, actual) => {
      return Math.abs(expected - actual) < 0.01;
    },
    
    orderNumber: (orderNum) => {
      return /^[A-Z0-9]{8,12}$/.test(orderNum);
    }
  }
};
```

### Registering Patterns

```javascript
// tinaa.config.js
module.exports = {
  patterns: [
    './patterns/ecommerce-checkout.js',
    './patterns/user-authentication.js',
    '@tinaa/patterns-banking' // npm package
  ]
};
```

## Custom Generators

### AI Prompt Templates

```javascript
// generators/form-validation.js
class FormValidationGenerator {
  constructor(ai) {
    this.ai = ai;
  }
  
  async generate(options) {
    const prompt = `
      Generate comprehensive form validation tests for ${options.url}.
      Include tests for:
      - Required fields
      - Field formats (email, phone, etc.)
      - Field length limits
      - Special characters
      - XSS prevention
      - Boundary values
    `;
    
    const response = await this.ai.complete(prompt, {
      model: 'gpt-4',
      temperature: 0.3
    });
    
    return this.parseResponse(response);
  }
}
```

### Domain-Specific Languages (DSL)

```javascript
// dsl/banking-dsl.js
class BankingDSL {
  constructor(page) {
    this.page = page;
  }
  
  async transferFunds(from, to, amount) {
    await this.page.click('[data-test="transfer-button"]');
    await this.page.selectOption('#from-account', from);
    await this.page.selectOption('#to-account', to);
    await this.page.fill('#amount', amount.toString());
    await this.page.click('[data-test="confirm-transfer"]');
  }
  
  async verifyBalance(account, expectedBalance) {
    const balance = await this.page.textContent(
      `[data-account="${account}"] .balance`
    );
    expect(parseFloat(balance)).toBe(expectedBalance);
  }
}
```

## Custom Assertions

### Creating Custom Matchers

```javascript
// matchers/accessibility.js
expect.extend({
  toBeAccessible: async (page, options = {}) => {
    const violations = await checkAccessibility(page, options);
    
    return {
      pass: violations.length === 0,
      message: () => violations.length > 0
        ? `Found ${violations.length} accessibility violations:\n${formatViolations(violations)}`
        : 'Page is accessible'
    };
  },
  
  toHaveAriaLabel: async (element, expectedLabel) => {
    const actualLabel = await element.getAttribute('aria-label');
    
    return {
      pass: actualLabel === expectedLabel,
      message: () => `Expected aria-label to be "${expectedLabel}", but got "${actualLabel}"`
    };
  }
});
```

### Using Custom Assertions

```javascript
test('checkout page accessibility', async ({ page }) => {
  await page.goto('/checkout');
  await expect(page).toBeAccessible({
    standards: ['WCAG2AA'],
    exclude: ['.third-party-widget']
  });
});
```

## Resource Packages

### Package Structure

```
tinaa-resources-finance/
├── package.json
├── index.js
├── patterns/
│   ├── trading.js
│   ├── banking.js
│   └── insurance.js
├── generators/
│   └── financial-forms.js
├── assertions/
│   └── currency.js
└── helpers/
    └── calculations.js
```

### Package Configuration

```json
{
  "name": "@company/tinaa-resources-finance",
  "version": "1.0.0",
  "main": "index.js",
  "tinaa": {
    "type": "resources",
    "patterns": ["./patterns/*.js"],
    "generators": ["./generators/*.js"],
    "assertions": ["./assertions/*.js"]
  }
}
```

## Custom Actions

### Defining Actions

```javascript
// actions/file-upload.js
module.exports = {
  name: 'uploadFile',
  
  async execute(page, options) {
    const { selector, filePath, waitForUpload = true } = options;
    
    // Handle file input
    const fileInput = await page.$(selector);
    await fileInput.setInputFiles(filePath);
    
    // Wait for upload completion
    if (waitForUpload) {
      await page.waitForSelector('.upload-complete', {
        timeout: 30000
      });
    }
    
    return {
      success: true,
      uploadedFile: filePath
    };
  }
};
```

### Registering Actions

```javascript
// Register globally
tinaa.registerAction('uploadFile', require('./actions/file-upload'));

// Use in tests
await tinaa.execute('uploadFile', {
  selector: '#file-input',
  filePath: './test-data/document.pdf'
});
```

## Custom Reporters

### Creating a Reporter

```javascript
// reporters/confluence-reporter.js
class ConfluenceReporter {
  constructor(options) {
    this.client = new ConfluenceClient(options);
  }
  
  async onTestComplete(test, result) {
    const page = await this.client.createPage({
      title: `Test Results: ${test.name}`,
      parent: this.options.parentPageId,
      content: this.formatResults(result)
    });
    
    if (result.screenshots) {
      await this.uploadScreenshots(page.id, result.screenshots);
    }
  }
  
  formatResults(result) {
    return `
      <h2>Test: ${result.name}</h2>
      <p>Status: ${result.status}</p>
      <p>Duration: ${result.duration}ms</p>
      ${result.error ? `<pre>${result.error}</pre>` : ''}
    `;
  }
}
```

## Best Practices

### 1. Modularity

Keep resources focused and single-purpose:
```javascript
// Good: Specific, reusable
const emailValidator = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

// Avoid: Too broad, hard to maintain
const validateEverything = (data) => { /* ... */ };
```

### 2. Documentation

Document your custom resources:
```javascript
/**
 * Validates credit card numbers using Luhn algorithm
 * @param {string} cardNumber - The card number to validate
 * @returns {boolean} True if valid
 * @example
 * validateCard('4111111111111111') // returns true
 */
function validateCard(cardNumber) {
  // Implementation
}
```

### 3. Testing

Test your custom resources:
```javascript
describe('Custom Banking Patterns', () => {
  it('should generate valid transfer tests', async () => {
    const pattern = new BankingPattern();
    const tests = await pattern.generate({
      accounts: ['checking', 'savings']
    });
    
    expect(tests).toContainTestStep('transferFunds');
  });
});
```

### 4. Version Management

- Use semantic versioning
- Document breaking changes
- Provide migration guides

## Sharing Resources

### Publishing to NPM

```bash
npm publish @yourcompany/tinaa-resources
```

### Private Registries

```json
// .npmrc
@yourcompany:registry=https://npm.company.com
```

### Community Marketplace

Share your resources with the community:
1. Create a GitHub repository
2. Add topic: `tinaa-resources`
3. Submit to [TINAA Marketplace](https://marketplace.tinaa.dev)

## Related Resources

- [SDK Development](sdk-development.md)
- [Plugin Development](../DEVELOPER_GUIDE.md#plugin-development)
- [API Reference](../API.md)
- [Pattern Examples](https://github.com/tinaa-examples/custom-patterns)