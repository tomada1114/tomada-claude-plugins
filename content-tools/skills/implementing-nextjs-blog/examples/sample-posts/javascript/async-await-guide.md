---
title: Understanding Async/Await in JavaScript
date: '2024-01-20'
excerpt: Master asynchronous programming with async/await syntax for cleaner, more readable code.
---

## What is Asynchronous Programming?

JavaScript is single-threaded, but it can handle asynchronous operations without blocking. This is essential for tasks like API calls, file reading, and timers.

## The Evolution of Async Code

### 1. Callbacks (The Old Way)

```javascript
function fetchData(callback) {
  setTimeout(() => {
    callback({ id: 1, name: 'Product' });
  }, 1000);
}

fetchData((data) => {
  console.log(data);
});
```

**Problem:** Callback hell when nesting multiple async operations.

### 2. Promises (Better)

```javascript
function fetchData() {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      resolve({ id: 1, name: 'Product' });
    }, 1000);
  });
}

fetchData()
  .then((data) => console.log(data))
  .catch((error) => console.error(error));
```

### 3. Async/Await (Best)

```javascript
async function getData() {
  try {
    const data = await fetchData();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}
```

## Practical Examples

### Fetching API Data

```javascript
async function fetchUsers() {
  try {
    const response = await fetch('https://api.example.com/users');

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const users = await response.json();
    return users;
  } catch (error) {
    console.error('Failed to fetch users:', error);
    throw error;
  }
}

// Usage
const users = await fetchUsers();
console.log(users);
```

### Parallel Execution with Promise.all

```javascript
async function fetchAllData() {
  const [users, products, orders] = await Promise.all([
    fetch('/api/users').then(r => r.json()),
    fetch('/api/products').then(r => r.json()),
    fetch('/api/orders').then(r => r.json()),
  ]);

  return { users, products, orders };
}
```

### Sequential vs Parallel

```javascript
// Sequential (slower)
async function sequential() {
  const user = await fetchUser();    // Wait 1s
  const posts = await fetchPosts();  // Wait 1s
  // Total: 2s
}

// Parallel (faster)
async function parallel() {
  const [user, posts] = await Promise.all([
    fetchUser(),   // Start immediately
    fetchPosts(),  // Start immediately
  ]);
  // Total: ~1s (whichever takes longer)
}
```

## Error Handling Patterns

### Try-Catch Block

```javascript
async function safeOperation() {
  try {
    const result = await riskyOperation();
    return { success: true, data: result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}
```

### Error Wrapper Function

```javascript
const asyncHandler = (fn) => (...args) => {
  return fn(...args).catch((error) => {
    console.error('Async error:', error);
    throw error;
  });
};

// Usage
const safeFetch = asyncHandler(async (url) => {
  const response = await fetch(url);
  return response.json();
});
```

## Best Practices

1. **Always use try-catch** for error handling
2. **Use Promise.all** for independent async operations
3. **Avoid mixing** callbacks with async/await
4. **Don't forget await** - easy to miss!
5. **Handle loading states** in UI code

> **Warning:** Forgetting `await` is a common bug. The code runs but doesn't wait for the result.

## Conclusion

Async/await makes asynchronous JavaScript code much cleaner and easier to understand. Combined with proper error handling, it's the recommended way to write modern JavaScript.
