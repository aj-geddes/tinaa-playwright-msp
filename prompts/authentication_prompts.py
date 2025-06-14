"""
User authentication prompt for Tina Tester MCP
"""

AUTHENTICATION_PROMPT = """
I need to authenticate to the website {site_url} to perform the requested testing.

Please provide your credentials in a secure manner. The credentials will only be used for this testing session and will not be stored permanently.

If you prefer not to share your actual credentials, you can:
1. Create a test account with limited permissions
2. Use a demo/sandbox environment if available
3. Let me know if there's a public test account I can use

How would you like to proceed with authentication?
"""

AUTHENTICATION_DISCLAIMER = """
IMPORTANT: I'll handle your credentials securely. They will only be used for this testing session and will not be stored after the session ends. For security best practices, consider changing your password after testing is complete if you've shared real credentials.
"""

CREDENTIAL_REQUEST = """
Please provide the following credentials for {site_url}:

- Username or Email: 
- Password:

Your credentials will be transmitted securely and only used for the current testing session.
"""
