---
title: Getting Started with JavaScript
date: '2024-01-15'
excerpt: Learn the fundamentals of JavaScript programming, from variables to functions.
---

## Introduction

JavaScript is one of the most popular programming languages in the world. It powers the interactive elements of websites and has expanded to server-side development with Node.js.

## Variables and Data Types

JavaScript has three ways to declare variables:

```javascript
// const - for values that won't change
const PI = 3.14159;

// let - for values that may change
let count = 0;
count = count + 1;

// var - older syntax (avoid in modern code)
var oldStyle = 'legacy';
```

### Common Data Types

| Type | Example | Description |
|------|---------|-------------|
| String | `'Hello'` | Text data |
| Number | `42` | Numeric values |
| Boolean | `true` | True or false |
| Array | `[1, 2, 3]` | Ordered list |
| Object | `{name: 'John'}` | Key-value pairs |

## Functions

Functions are reusable blocks of code:

```javascript
// Traditional function
function greet(name) {
  return `Hello, ${name}!`;
}

// Arrow function (ES6+)
const greetArrow = (name) => `Hello, ${name}!`;

// Usage
console.log(greet('World')); // "Hello, World!"
```

## Control Flow

### Conditionals

```javascript
const score = 85;

if (score >= 90) {
  console.log('Excellent!');
} else if (score >= 70) {
  console.log('Good job!');
} else {
  console.log('Keep practicing!');
}
```

### Loops

```javascript
// For loop
for (let i = 0; i < 5; i++) {
  console.log(`Iteration ${i}`);
}

// For...of (arrays)
const fruits = ['apple', 'banana', 'orange'];
for (const fruit of fruits) {
  console.log(fruit);
}

// forEach method
fruits.forEach((fruit, index) => {
  console.log(`${index}: ${fruit}`);
});
```

## Next Steps

Now that you understand the basics, try:

1. Building a simple calculator
2. Creating a to-do list
3. Learning about DOM manipulation

> **Tip:** Practice makes perfect! Write code every day to improve your skills.

## Conclusion

JavaScript is a versatile language that opens many doors in web development. Keep learning and building projects to solidify your understanding.
