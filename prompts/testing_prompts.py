"""
Testing prompts for Tina Tester MCP
"""

EXPLORATORY_TEST_PROMPT = """
I'll perform an exploratory test of {url} focusing on {focus_area}.

During this test, I'll:
1. Navigate through the site systematically
2. Observe the UI, functionality, and user experience
3. Document any issues or observations
4. Apply testing heuristics to identify potential problems
5. Suggest improvements based on best practices

I'll use the following testing techniques:
- Boundary value analysis
- Error guessing
- Feature combination testing
- State transition testing
- User-centered testing

I'll provide a detailed report of my findings, including:
- Issues discovered (categorized by severity)
- Screenshots of problematic areas
- Recommendations for improvement
- Suggestions for further testing

Is there anything specific you'd like me to focus on during this exploratory test?
"""

ACCESSIBILITY_TEST_PROMPT = """
I'll perform an accessibility test of {url} to ensure it's usable by people with disabilities.

During this test, I'll check compliance with WCAG 2.1 guidelines, focusing on:

1. Perceivable content:
   - Text alternatives for non-text content
   - Captions and alternatives for multimedia
   - Content adaptability and distinguishability

2. Operable interface:
   - Keyboard accessibility
   - Sufficient time for interactions
   - Navigation and input methods

3. Understandable information:
   - Readability and predictability
   - Input assistance and error prevention

4. Robust content:
   - Compatibility with assistive technologies

I'll provide a detailed report with:
- Accessibility issues discovered (categorized by WCAG criteria)
- Screenshots and code examples of problematic areas
- Recommendations for remediation
- Potential impact on users with disabilities

Would you like me to focus on any specific accessibility concerns?
"""

RESPONSIVE_TEST_PROMPT = """
I'll perform responsive design testing of {url} to ensure it works well across different devices and screen sizes.

During this test, I'll:
1. Test the site at standard breakpoints:
   - Mobile Small (320×568px)
   - Mobile Medium (375×667px)
   - Mobile Large (414×736px)
   - Tablet (768×1024px)
   - Laptop (1366×768px)
   - Desktop (1920×1080px)

2. Check for:
   - Layout integrity and readability
   - Navigation usability
   - Touch target sizes on mobile
   - Content prioritization
   - Image and media scaling
   - Form usability across devices

I'll provide a detailed report with:
- Screenshots at each breakpoint
- Identified responsive design issues
- Recommendations for improvement
- Comparative analysis across devices

Are there any specific devices or screen sizes you'd like me to focus on?
"""

FORM_TEST_PROMPT = """
I'll perform comprehensive testing of the form at {url} to ensure it functions correctly and provides a good user experience.

During this test, I'll check:

1. Functionality:
   - Field validation (required fields, format validation)
   - Error messages (clarity, helpfulness, accessibility)
   - Submission process and success/failure handling
   - Default values and field pre-population

2. Usability:
   - Field labels and instructions
   - Tab order and keyboard navigation
   - Input assistance features
   - Mobile-friendliness of inputs

3. Accessibility:
   - ARIA attributes and screen reader compatibility
   - Color contrast of form elements
   - Keyboard accessibility
   - Error identification methods

I'll test with various input scenarios:
- Valid inputs
- Invalid formats
- Boundary values
- Empty submissions
- Special characters and edge cases

I'll provide a detailed report with:
- Functional issues discovered
- Usability observations
- Screenshots of problematic areas
- Recommendations for improvement

Would you like me to focus on any specific aspects of the form?
"""

SECURITY_TEST_BASIC_PROMPT = """
I'll perform basic security testing of {url} to identify common security issues. 

Note: This is a non-invasive assessment that doesn't attempt to exploit vulnerabilities.

During this test, I'll check for:

1. Transport security:
   - HTTPS implementation
   - Certificate validity
   - HTTP security headers
   - Secure cookie attributes

2. Client-side security:
   - Visible information exposure
   - Form security features
   - Content Security Policy
   - Cross-site scripting protections

3. Authentication features (if applicable):
   - Login form security
   - Password policies
   - Account lockout mechanisms
   - Session management

I'll provide a detailed report with:
- Security observations (without exploitation attempts)
- Best practice recommendations
- References to security standards
- Suggestions for further security assessment

Is there a specific security aspect you'd like me to focus on?
"""

TEST_REPORT_TEMPLATE = """
# Test Report: {test_type} for {url}

## Summary
{summary}

## Test Environment
- Date: {date}
- Browser: {browser}
- Viewport: {viewport}
- Device: {device}

## Findings

### High Priority Issues
{high_priority_issues}

### Medium Priority Issues
{medium_priority_issues}

### Low Priority Issues
{low_priority_issues}

## Recommendations
{recommendations}

## Screenshots
{screenshots}

## Next Steps
{next_steps}
"""
