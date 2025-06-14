# SDK Development Guide

Learn how to develop SDKs and extensions for TINAA to support additional languages and frameworks.

## SDK Architecture

### Core Components

```typescript
interface TinaaSDK {
  // Test generation
  generate(options: GenerateOptions): Promise<TestSuite>;

  // Test execution
  run(tests: Test[]): Promise<TestResults>;

  // AI integration
  ai: AIService;

  // Plugin system
  plugins: PluginManager;
}
```

## Creating a Language SDK

### Step 1: Define the Interface

```typescript
// tinaa-sdk-python/src/types.ts
export interface PythonSDK extends TinaaSDK {
  pythonVersion: string;
  pipenvSupport: boolean;
  pytestIntegration: boolean;
}
```

### Step 2: Implement Core Features

```typescript
// tinaa-sdk-python/src/index.ts
export class TinaaPythonSDK implements PythonSDK {
  async generate(options: GenerateOptions): Promise<TestSuite> {
    // Convert AI output to Python/pytest format
    const aiResponse = await this.ai.generateTests(options);
    return this.convertToPython(aiResponse);
  }

  private convertToPython(tests: AIGeneratedTests): TestSuite {
    // Transform to Python syntax
    return new PythonTestSuite(tests);
  }
}
```

### Step 3: Add Language-Specific Features

```python
# Generated Python test example
import pytest
from playwright.sync_api import Page, expect

class TestLoginFlow:
    def test_successful_login(self, page: Page):
        """AI-generated test for login functionality"""
        page.goto("https://example.com/login")
        page.fill("#email", "user@example.com")
        page.fill("#password", "password123")
        page.click("button[type='submit']")
        expect(page).to_have_url("https://example.com/dashboard")
```

## Plugin Development

### Plugin Structure

```javascript
// tinaa-plugin-visual/index.js
module.exports = {
  name: 'visual-testing',
  version: '1.0.0',

  hooks: {
    beforeTest: async (test, context) => {
      // Setup visual testing
    },

    afterTest: async (test, result, context) => {
      // Compare screenshots
    }
  },

  commands: {
    'visual:approve': async (args) => {
      // Approve visual changes
    }
  }
};
```

### Registering Plugins

```javascript
// tinaa.config.js
module.exports = {
  plugins: [
    '@tinaa/plugin-visual',
    '@tinaa/plugin-accessibility',
    './custom-plugins/my-plugin'
  ]
};
```

## API Client Libraries

### TypeScript/JavaScript Client

```typescript
import { TinaaClient } from '@tinaa/client';

const client = new TinaaClient({
  apiKey: process.env.TINAA_API_KEY,
  baseURL: 'https://api.tinaa.dev'
});

// Generate tests
const tests = await client.generate({
  url: 'https://example.com',
  prompt: 'Test checkout flow'
});
```

### Python Client

```python
from tinaa import TinaaClient

client = TinaaClient(
    api_key=os.environ['TINAA_API_KEY']
)

# Generate tests
tests = client.generate(
    url='https://example.com',
    prompt='Test checkout flow'
)
```

## Framework Integration

### Jest Integration

```javascript
// jest-tinaa-reporter.js
class TinaaReporter {
  onTestResult(test, testResult) {
    // Send results to TINAA
    this.client.reportResults({
      suite: test.path,
      results: testResult
    });
  }
}
```

### Pytest Integration

```python
# pytest_tinaa.py
import pytest
from tinaa import TinaaReporter

@pytest.hookimpl
def pytest_runtest_makereport(item, call):
    """Send test results to TINAA"""
    reporter = TinaaReporter()
    reporter.send_result(item, call)
```

## Best Practices

### 1. Consistent API Design

- Follow TINAA's core API patterns
- Use similar method names and signatures
- Maintain backward compatibility

### 2. Error Handling

```typescript
try {
  const result = await sdk.generate(options);
} catch (error) {
  if (error instanceof TinaaAuthError) {
    // Handle auth errors
  } else if (error instanceof TinaaGenerationError) {
    // Handle generation errors
  }
}
```

### 3. Documentation

- Provide comprehensive API docs
- Include code examples
- Document breaking changes

### 4. Testing

```javascript
describe('TinaaSDK', () => {
  it('should generate valid tests', async () => {
    const sdk = new TinaaSDK();
    const tests = await sdk.generate({
      url: 'https://example.com',
      prompt: 'Test login'
    });
    expect(tests).toHaveProperty('suite');
    expect(tests.suite.tests).toHaveLength.greaterThan(0);
  });
});
```

## Publishing SDKs

### NPM Package

```json
{
  "name": "@tinaa/sdk-python",
  "version": "1.0.0",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "peerDependencies": {
    "@tinaa/core": "^2.0.0"
  }
}
```

### PyPI Package

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name='tinaa-sdk',
    version='1.0.0',
    packages=find_packages(),
    install_requires=[
        'requests>=2.28.0',
        'pydantic>=1.10.0'
    ]
)
```

## Community SDKs

Current community-developed SDKs:
- Ruby SDK
- Go SDK
- Java SDK
- .NET SDK

## Getting Help

- [Developer Forum](https://github.com/aj-geddes/tinaa-playwright-msp/discussions/categories/developers)
- [SDK Examples](https://github.com/tinaa-examples/sdk-development)
- [API Documentation](../API.md)

## Related Resources

- [Custom Resources Guide](custom-resources.md)
- [Plugin Development](../DEVELOPER_GUIDE.md#plugin-development)
- [API Reference](../API.md)