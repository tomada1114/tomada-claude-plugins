---
title: Introduction to React Hooks
date: '2024-02-01'
excerpt: Learn how to use React Hooks to add state and lifecycle features to functional components.
---

## What Are React Hooks?

Hooks are functions that let you use state and other React features in functional components. They were introduced in React 16.8.

## useState Hook

The most basic hook for managing component state.

```tsx
import { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);

  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  );
}
```

### Multiple State Variables

```tsx
function UserForm() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [isSubscribed, setIsSubscribed] = useState(false);

  return (
    <form>
      <input
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <input
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <label>
        <input
          type="checkbox"
          checked={isSubscribed}
          onChange={(e) => setIsSubscribed(e.target.checked)}
        />
        Subscribe to newsletter
      </label>
    </form>
  );
}
```

## useEffect Hook

For side effects like data fetching, subscriptions, and DOM manipulation.

```tsx
import { useState, useEffect } from 'react';

function UserProfile({ userId }: { userId: string }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchUser() {
      setLoading(true);
      try {
        const response = await fetch(`/api/users/${userId}`);
        const data = await response.json();
        setUser(data);
      } finally {
        setLoading(false);
      }
    }

    fetchUser();
  }, [userId]); // Re-run when userId changes

  if (loading) return <p>Loading...</p>;
  if (!user) return <p>User not found</p>;

  return <h1>{user.name}</h1>;
}
```

### Cleanup Function

```tsx
useEffect(() => {
  const subscription = eventEmitter.subscribe(handleEvent);

  // Cleanup function runs on unmount or before re-running
  return () => {
    subscription.unsubscribe();
  };
}, []);
```

## useContext Hook

Share data across components without prop drilling.

```tsx
import { createContext, useContext, useState } from 'react';

// Create context
const ThemeContext = createContext({ theme: 'light', toggle: () => {} });

// Provider component
function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');

  const toggle = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

// Consumer component
function ThemedButton() {
  const { theme, toggle } = useContext(ThemeContext);

  return (
    <button
      onClick={toggle}
      style={{
        background: theme === 'light' ? '#fff' : '#333',
        color: theme === 'light' ? '#333' : '#fff',
      }}
    >
      Toggle Theme
    </button>
  );
}
```

## Custom Hooks

Create reusable logic by extracting hooks into custom functions.

```tsx
// useLocalStorage.ts
function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch {
      return initialValue;
    }
  });

  const setValue = (value: T | ((val: T) => T)) => {
    const valueToStore = value instanceof Function
      ? value(storedValue)
      : value;
    setStoredValue(valueToStore);
    window.localStorage.setItem(key, JSON.stringify(valueToStore));
  };

  return [storedValue, setValue] as const;
}

// Usage
function App() {
  const [name, setName] = useLocalStorage('name', '');

  return (
    <input value={name} onChange={(e) => setName(e.target.value)} />
  );
}
```

## Rules of Hooks

1. **Only call hooks at the top level** - not inside loops, conditions, or nested functions
2. **Only call hooks from React functions** - functional components or custom hooks

```tsx
// ❌ Wrong
if (condition) {
  const [value, setValue] = useState(0);
}

// ✅ Correct
const [value, setValue] = useState(0);
if (condition) {
  // use value here
}
```

## Conclusion

React Hooks revolutionized how we write React components. They make code more reusable, testable, and easier to understand. Start with `useState` and `useEffect`, then explore other hooks as needed.
