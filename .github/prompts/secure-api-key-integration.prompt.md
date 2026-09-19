---
description: "Securely configure or review an API key integration in the workspace"
name: "Secure API Key Integration"
argument-hint: "Describe the provider, intended API operation, and current implementation or error"
agent: "agent"
---

Handle this API-key integration request: ${input:apiKeyTask}

Inspect the relevant workspace code and documentation before making changes. Determine the owning backend integration and preserve the existing framework and configuration conventions.

Requirements:
- Never ask the user to paste a live API key, and never place a secret in source code, frontend assets, committed configuration, logs, screenshots, tests, or the final response.
- Keep API keys server-side. Use environment variables or the repository's existing secret-management mechanism, with a clear non-secret configuration name and a safe missing-key error.
- Reuse existing HTTP clients, settings objects, error handling, and dependency patterns where available.
- If the request requires code changes, make the smallest focused edit and add or update targeted tests when the repository has a suitable test pattern.
- Document only the setup steps needed to provide the key securely, including the variable name, provider restrictions, and the validation command or endpoint. Use placeholders such as `your-api-key`; never invent a real credential.
- Check for accidental exposure in frontend code, tracked files, logs, and error messages.

Return:
1. A concise summary of the change or review result.
2. Files changed, with the purpose of each.
3. Secure setup instructions using placeholder values only.
4. Validation performed and any remaining limitations.
