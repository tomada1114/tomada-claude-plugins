---
name: http-status-guide
description: Explain HTTP status codes with examples and best practices. Use when working with APIs, debugging HTTP responses, or learning about REST API design and HTTP protocol.
---

# HTTP Status Code Guide

This skill helps you understand and use HTTP status codes correctly in API development and debugging. Demonstrates the use of reference files for detailed information.

## When to Use This Skill

Use this skill when:
- Debugging API responses
- Designing REST API endpoints
- Learning about HTTP protocol
- Choosing appropriate status codes for different scenarios
- Troubleshooting web applications

## Core Concepts

HTTP status codes are three-digit codes that indicate the result of an HTTP request. They are grouped into five categories:

- **1xx (Informational)**: Request received, continuing process
- **2xx (Success)**: Request successfully received, understood, and accepted
- **3xx (Redirection)**: Further action needed to complete the request
- **4xx (Client Error)**: Request contains bad syntax or cannot be fulfilled
- **5xx (Server Error)**: Server failed to fulfill a valid request

## Quick Reference

For detailed information about all status codes, see [reference.md](reference.md).

### Most Common Status Codes

**Success:**
- `200 OK`: Standard success response
- `201 Created`: Resource successfully created
- `204 No Content`: Success with no response body

**Client Errors:**
- `400 Bad Request`: Invalid request syntax
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Server refuses to authorize
- `404 Not Found`: Resource doesn't exist

**Server Errors:**
- `500 Internal Server Error`: Generic server error
- `503 Service Unavailable`: Server temporarily unavailable

## Instructions

When helping with HTTP status codes:

1. **Identify the scenario**: Understand what the API endpoint does
2. **Choose appropriate code**: Select the most specific applicable code
3. **Provide example**: Show how to use it in context
4. **Explain reasoning**: Clarify why this code is appropriate

## Examples

### Example 1: Creating a New User

```javascript
// POST /api/users
app.post('/api/users', async (req, res) => {
  try {
    const user = await createUser(req.body);
    // Use 201 Created for successful resource creation
    res.status(201).json({
      id: user.id,
      message: 'User created successfully'
    });
  } catch (error) {
    // Use 400 Bad Request for validation errors
    res.status(400).json({
      error: 'Invalid user data',
      details: error.message
    });
  }
});
```

### Example 2: Authentication Error

```javascript
// GET /api/protected-resource
app.get('/api/protected-resource', async (req, res) => {
  const token = req.headers.authorization;

  if (!token) {
    // Use 401 Unauthorized when authentication is required
    return res.status(401).json({
      error: 'Authentication required',
      message: 'Please provide a valid token'
    });
  }

  // Process authenticated request...
});
```

## Best Practices

- Use the most specific status code that applies
- Always include a response body with error details
- Be consistent across your API
- Follow RESTful conventions
- Document your API's status code usage

See [reference.md](reference.md) for comprehensive best practices.

## AI Assistant Instructions

When this skill is activated:

1. **Analyze the scenario**: Understand what the user is trying to accomplish
2. **Recommend status code**: Choose the most appropriate code
3. **Provide code example**: Show implementation in their language/framework
4. **Explain alternatives**: Discuss other codes that might apply
5. **Reference documentation**: Point to [reference.md](reference.md) for deeper information

Always:
- Explain why a particular status code is appropriate
- Provide working code examples
- Consider the full context (REST conventions, API design)
- Suggest response body structure

Never:
- Recommend generic codes when specific ones apply
- Use 200 OK for errors
- Ignore the semantic meaning of status codes
