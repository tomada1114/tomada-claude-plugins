# HTTP Status Codes - Complete Reference

This file contains detailed information about HTTP status codes. It's loaded on-demand when needed, keeping the main SKILL.md concise.

## 1xx Informational Responses

### 100 Continue
The client should continue with its request. Used with large uploads.

**Example:**
```http
HTTP/1.1 100 Continue
```

### 101 Switching Protocols
Server is switching protocols as requested by the client (e.g., WebSocket upgrade).

**Example:**
```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
```

### 102 Processing (WebDAV)
Server has received and is processing the request, but no response is available yet.

---

## 2xx Success

### 200 OK
Standard response for successful HTTP requests.

**Use when:**
- GET request returns data
- PUT/PATCH request updates a resource
- DELETE request succeeds and returns data

**Example:**
```javascript
res.status(200).json({ users: [...] });
```

### 201 Created
Request succeeded and a new resource was created.

**Use when:**
- POST request creates a new resource
- Should include Location header with new resource URI

**Example:**
```javascript
res.status(201)
   .location(`/api/users/${user.id}`)
   .json({ id: user.id, name: user.name });
```

### 202 Accepted
Request accepted for processing but not yet completed.

**Use when:**
- Async operations (e.g., background jobs)
- Request queued for later processing

**Example:**
```javascript
res.status(202).json({
  message: 'Job queued',
  jobId: 'job-123',
  statusUrl: '/api/jobs/job-123'
});
```

### 204 No Content
Request succeeded but no content to return.

**Use when:**
- DELETE request succeeds
- PUT request succeeds with no response body
- API operation completes without returning data

**Example:**
```javascript
res.status(204).send();
```

### 206 Partial Content
Server is delivering only part of the resource due to a range request.

**Use when:**
- Video streaming
- Large file downloads with resume capability
- Pagination with range headers

---

## 3xx Redirection

### 301 Moved Permanently
Resource has permanently moved to a new URL.

**Use when:**
- Permanent URL changes
- Old endpoints deprecated in favor of new ones

**Example:**
```javascript
res.status(301)
   .location('/api/v2/users')
   .send();
```

### 302 Found (Temporary Redirect)
Resource temporarily at different URL.

**Use when:**
- Temporary redirects
- A/B testing
- Temporary maintenance pages

### 304 Not Modified
Resource hasn't changed since last request (uses caching headers).

**Use when:**
- Implementing HTTP caching
- Client has cached version that's still valid

**Example:**
```javascript
if (req.headers['if-none-match'] === etag) {
  res.status(304).send();
}
```

### 307 Temporary Redirect
Like 302, but guarantees request method won't change.

### 308 Permanent Redirect
Like 301, but guarantees request method won't change.

---

## 4xx Client Errors

### 400 Bad Request
Server cannot process request due to client error.

**Use when:**
- Invalid JSON syntax
- Missing required fields
- Invalid parameter format
- Validation errors

**Example:**
```javascript
res.status(400).json({
  error: 'Bad Request',
  message: 'Missing required field: email',
  fields: { email: 'Email is required' }
});
```

### 401 Unauthorized
Authentication is required and has failed or not been provided.

**Use when:**
- No authentication credentials provided
- Invalid credentials
- Expired token

**Example:**
```javascript
res.status(401).json({
  error: 'Unauthorized',
  message: 'Invalid or expired token',
  requiresAuth: true
});
```

**Note:** Despite the name, this actually means "unauthenticated" not "unauthorized".

### 403 Forbidden
Server understands request but refuses to authorize it.

**Use when:**
- User authenticated but lacks permissions
- Resource access denied
- IP blocked

**Example:**
```javascript
res.status(403).json({
  error: 'Forbidden',
  message: 'You do not have permission to access this resource'
});
```

### 404 Not Found
Requested resource doesn't exist.

**Use when:**
- Resource ID doesn't exist
- Endpoint doesn't exist
- File not found

**Example:**
```javascript
res.status(404).json({
  error: 'Not Found',
  message: 'User with id 123 not found'
});
```

### 405 Method Not Allowed
HTTP method not supported for this endpoint.

**Use when:**
- POST to read-only endpoint
- DELETE on non-deletable resource

**Example:**
```javascript
res.status(405)
   .set('Allow', 'GET, POST')
   .json({
     error: 'Method Not Allowed',
     message: 'Only GET and POST are allowed on this endpoint'
   });
```

### 409 Conflict
Request conflicts with current state of the server.

**Use when:**
- Duplicate resource creation
- Version conflicts
- Business rule violations

**Example:**
```javascript
res.status(409).json({
  error: 'Conflict',
  message: 'User with this email already exists'
});
```

### 410 Gone
Resource permanently deleted (stronger than 404).

**Use when:**
- Resource intentionally removed
- Deleted user accounts
- Expired content

### 422 Unprocessable Entity
Request well-formed but semantically incorrect.

**Use when:**
- Validation errors (alternative to 400)
- Business logic validation fails
- Invalid state transitions

**Example:**
```javascript
res.status(422).json({
  error: 'Unprocessable Entity',
  message: 'Validation failed',
  errors: {
    email: 'Email format is invalid',
    age: 'Age must be at least 18'
  }
});
```

### 429 Too Many Requests
User has sent too many requests in a given time (rate limiting).

**Use when:**
- Rate limit exceeded
- DDoS protection triggered

**Example:**
```javascript
res.status(429)
   .set('Retry-After', '60')
   .json({
     error: 'Too Many Requests',
     message: 'Rate limit exceeded. Try again in 60 seconds'
   });
```

---

## 5xx Server Errors

### 500 Internal Server Error
Generic server error when no more specific message is suitable.

**Use when:**
- Unexpected errors occur
- Database connection fails
- Unhandled exceptions

**Example:**
```javascript
res.status(500).json({
  error: 'Internal Server Error',
  message: 'An unexpected error occurred'
});
```

**Note:** Avoid exposing stack traces or internal details to clients in production.

### 501 Not Implemented
Server doesn't support the functionality required.

**Use when:**
- Feature not yet implemented
- Unsupported HTTP method

### 502 Bad Gateway
Server received invalid response from upstream server.

**Use when:**
- Proxy/gateway errors
- Microservice communication failures

### 503 Service Unavailable
Server temporarily unable to handle request.

**Use when:**
- Scheduled maintenance
- Server overloaded
- Database temporarily unavailable

**Example:**
```javascript
res.status(503)
   .set('Retry-After', '300')
   .json({
     error: 'Service Unavailable',
     message: 'Scheduled maintenance in progress. Try again in 5 minutes'
   });
```

### 504 Gateway Timeout
Server didn't receive timely response from upstream server.

**Use when:**
- Upstream timeout
- Long-running operations timeout

---

## Best Practices by Scenario

### Creating Resources (POST)
- Success: `201 Created` with Location header
- Validation error: `400 Bad Request` or `422 Unprocessable Entity`
- Duplicate: `409 Conflict`
- Unauthorized: `401 Unauthorized`

### Updating Resources (PUT/PATCH)
- Success with response: `200 OK`
- Success without response: `204 No Content`
- Not found: `404 Not Found`
- Validation error: `400 Bad Request` or `422 Unprocessable Entity`
- Conflict: `409 Conflict`

### Deleting Resources (DELETE)
- Success with response: `200 OK`
- Success without response: `204 No Content`
- Not found: `404 Not Found`
- Already deleted: `410 Gone`

### Reading Resources (GET)
- Success: `200 OK`
- Not found: `404 Not Found`
- Cached: `304 Not Modified`
- Partial: `206 Partial Content`

### Authentication & Authorization
- No credentials: `401 Unauthorized`
- Invalid credentials: `401 Unauthorized`
- Valid credentials, insufficient permissions: `403 Forbidden`

### Validation & Business Logic
- Syntax errors: `400 Bad Request`
- Semantic errors: `422 Unprocessable Entity`
- Business rule violations: `409 Conflict` or `422 Unprocessable Entity`

---

## Response Body Best Practices

### Error Response Structure

Always include helpful error information:

```javascript
{
  "error": "Brief error type",
  "message": "Human-readable description",
  "details": {
    // Additional context
  },
  "timestamp": "2025-01-15T10:30:00Z",
  "path": "/api/users",
  "requestId": "req-123"
}
```

### Success Response Structure

Be consistent across your API:

```javascript
{
  "data": {
    // Your resource or resources
  },
  "meta": {
    // Metadata (pagination, etc.)
  }
}
```

---

## Status Code Decision Tree

```
Is the request successful?
├─ Yes
│  ├─ Is a resource created? → 201 Created
│  ├─ Is there response data? → 200 OK
│  └─ No response data? → 204 No Content
│
└─ No
   ├─ Is it a client error?
   │  ├─ Authentication problem? → 401 Unauthorized
   │  ├─ Permission problem? → 403 Forbidden
   │  ├─ Resource not found? → 404 Not Found
   │  ├─ Validation error? → 400 Bad Request or 422 Unprocessable Entity
   │  ├─ Conflict? → 409 Conflict
   │  └─ Rate limited? → 429 Too Many Requests
   │
   └─ Is it a server error?
      ├─ Server unavailable? → 503 Service Unavailable
      ├─ Upstream timeout? → 504 Gateway Timeout
      └─ Generic error? → 500 Internal Server Error
```

---

## Common Mistakes to Avoid

1. **Using 200 for errors**: Never return 200 with an error in the body
2. **Wrong authentication codes**: Use 401 for authentication, 403 for authorization
3. **Generic codes**: Use specific codes when available (422 vs 400, 409 vs 400)
4. **Missing response bodies**: Always include helpful error messages
5. **Inconsistent responses**: Maintain same structure across all endpoints
6. **Exposing internals**: Don't leak stack traces or database errors in production

---

## Framework-Specific Examples

### Express.js
```javascript
app.use((err, req, res, next) => {
  if (err.name === 'ValidationError') {
    return res.status(422).json({
      error: 'Validation Error',
      details: err.errors
    });
  }

  res.status(500).json({
    error: 'Internal Server Error'
  });
});
```

### FastAPI (Python)
```python
from fastapi import HTTPException

@app.post("/users", status_code=201)
async def create_user(user: User):
    if await user_exists(user.email):
        raise HTTPException(
            status_code=409,
            detail="User with this email already exists"
        )
    return await create_user_in_db(user)
```

### Django REST Framework (Python)
```python
from rest_framework import status
from rest_framework.response import Response

def create(self, request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )
    return Response(
        serializer.errors,
        status=status.HTTP_422_UNPROCESSABLE_ENTITY
    )
```
