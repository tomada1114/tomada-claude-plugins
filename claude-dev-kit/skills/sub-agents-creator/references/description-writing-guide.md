# Description Writing Guide

サブエージェントの `description` フィールドは、エージェントがいつ、どのように呼び出されるかを決定する最も重要な要素です。このガイドでは、効果的な description の書き方を段階的に説明します。

## 基本構造

効果的な description は以下の3要素を含みます：

```
[何をするか] + [いつ使うか] + [具体例/キーワード]
```

### 最小構成（避けるべき）

```yaml
description: Code reviewer
```

**問題点**:
- ❌ いつ使うべきかが不明
- ❌ トリガーワードが少なすぎる
- ❌ 自動呼び出しされない

### 基本構成（最低限）

```yaml
description: Expert code review specialist. Use when reviewing code changes for quality and security.
```

**改善点**:
- ✅ 役割が明確（Expert code review specialist）
- ✅ 使用タイミングが明示（when reviewing code changes）
- ✅ 目的が明確（quality and security）

### 推奨構成

```yaml
description: Expert code review specialist for quality, security, and maintainability. Use PROACTIVELY after writing or modifying code to ensure high development standards.
```

**強化点**:
- ✅ `Use PROACTIVELY` で自動呼び出しを促進
- ✅ 具体的な品質要素（quality, security, maintainability）
- ✅ トリガーシナリオが明確（after writing or modifying code）

## 積極的呼び出しパターン

### レベル1: 通常（受動的）

```yaml
description: Mobile development specialist. Use when working with React Native or Flutter.
```

**特徴**:
- ユーザーが明示的に「mobile」「React Native」などを言及した時のみ起動
- 自動提案は少ない

### レベル2: 積極的（PROACTIVELY）

```yaml
description: Cross-platform mobile development specialist for React Native and Flutter. Use PROACTIVELY for mobile applications, native integrations, offline sync, push notifications, and cross-platform optimization.
```

**特徴**:
- ✅ `Use PROACTIVELY for` でClaude自身が使用を提案
- ✅ 具体的なユースケースを列挙（native integrations, push notifications など）
- ✅ より広範囲のコンテキストで自動起動

**実例**: `mobile-developer.md`

### レベル3: 強制的（MUST BE USED）

```yaml
description: Expo MCP Server integration specialist. MUST BE USED for all Expo MCP-related tasks including documentation search, library installation, automation testing, and AI-assisted development workflows. Use PROACTIVELY when working with Expo projects, mobile app testing, or AI-powered development automation.
```

**特徴**:
- ✅ `MUST BE USED` で義務的な使用を指示
- ✅ 明確なスコープ定義（all Expo MCP-related tasks）
- ✅ `PROACTIVELY` も併用して広範囲カバー
- ✅ 詳細なタスクリスト（documentation search, library installation など）

**実例**: `expo-mcp-specialist.md`

### レベル4: Examples付き（最高品質）

```yaml
description: Use this agent to review code for architectural consistency and patterns. Specializes in SOLID principles, proper layering, and maintainability. Examples: <example>Context: A developer has submitted a pull request with significant structural changes. user: 'Please review the architecture of this new feature.' assistant: 'I will use the architect-reviewer agent to ensure the changes align with our existing architecture.' <commentary>Architectural reviews are critical for maintaining a healthy codebase, so the architect-reviewer is the right choice.</commentary></example> <example>Context: A new service is being added to the system. user: 'Can you check if this new service is designed correctly?' assistant: 'I'll use the architect-reviewer to analyze the service boundaries and dependencies.' <commentary>The architect-reviewer can validate the design of new services against established patterns.</commentary></example>
```

**特徴**:
- ✅ `<example>` タグで具体的なシナリオを提示
- ✅ Context + user + assistant + commentary の構造
- ✅ 複数の使用例で理解を深める
- ✅ 最も精度の高い自動呼び出し

**実例**: `architect-reviewer.md`

## Examples タグの使い方

### 基本構造

```xml
<example>
Context: [状況説明]
user: '[ユーザーの発言]'
assistant: '[Claudeの応答]'
<commentary>[なぜこのエージェントが適切か]</commentary>
</example>
```

### 単一Example

```yaml
description: Database migration specialist. Examples: <example>Context: Schema changes needed. user: 'Create migration for new users table' assistant: 'Using db-migration agent for safe schema updates.' <commentary>Ensures migration best practices.</commentary></example>
```

### 複数Examples

```yaml
description: Security auditor. Examples: <example>Context: New auth feature. user: 'Review authentication flow' assistant: 'Security-auditor will check for vulnerabilities.' <commentary>Critical for auth security.</commentary></example> <example>Context: API endpoint added. user: 'Check API security' assistant: 'Using security-auditor for OWASP compliance.' <commentary>Prevents common security flaws.</commentary></example>
```

### いつ使うべきか

**✅ Examples を使うべき場合**:
- 複雑な判断基準が必要なエージェント
- 他のエージェントと役割が重複しうる場合
- 特定のコンテキストでのみ起動すべき場合
- 高精度な自動呼び出しが必要な場合

**❌ Examples が不要な場合**:
- シンプルで明確な役割（code-reviewer など）
- ユニークなキーワードで十分識別可能
- 短い description で十分伝わる

## トリガーワード戦略

### ドメイン固有の用語を含める

**✅ 良い例**:
```yaml
description: React Native specialist for Expo, expo-router, NativeWind, GlueStack UI, native modules, and cross-platform development.
```

**キーワード**: React Native, Expo, expo-router, NativeWind, GlueStack UI, native modules, cross-platform

**❌ 悪い例**:
```yaml
description: Mobile app development helper.
```

**問題**: 「mobile app」は一般的すぎて他のエージェントと競合する可能性

### 類義語を網羅する

```yaml
description: API documentation generator for REST, GraphQL, OpenAPI, Swagger, and API specifications.
```

**カバー範囲**:
- REST → RESTful API
- GraphQL → GraphQL schema
- OpenAPI / Swagger → 両方の用語
- API specifications → 一般的な表現

### ユーザーの自然な言葉遣いを予測

**ユーザーが言いそうなこと**:
- "Add camera functionality"
- "How do I use the camera?"
- "Implement photo capture"

**対応する description**:
```yaml
description: Camera integration specialist. Use when adding camera functionality, implementing photo/video capture, or working with expo-camera, image picker, or media libraries.
```

### 技術スタックを明示

```yaml
description: TypeScript expert for advanced type system features, generic constraints, conditional types, type inference, and strict typing patterns. Use PROACTIVELY when working with complex TypeScript code, type definitions, or migrating from JavaScript.
```

**明示されている技術**:
- TypeScript（主要）
- generic constraints, conditional types（高度な機能）
- JavaScript migration（移行シナリオ）

## 長さの最適化（1024文字制限）

### 問題: description が長すぎる

```yaml
description: This is a comprehensive mobile development specialist that can help you with React Native development, Flutter development, native module integration for both iOS and Android platforms, offline-first data synchronization strategies, push notification implementation using Firebase Cloud Messaging or Apple Push Notification Service, deep linking configuration, app performance optimization techniques, bundle size reduction, app store submission requirements for both Apple App Store and Google Play Store, and cross-platform development best practices.
# 文字数: 500+ 文字（冗長）
```

### 解決策1: 箇条書きをカンマ区切りに

```yaml
description: Cross-platform mobile specialist for React Native, Flutter, native modules (iOS/Android), offline sync, push notifications (FCM/APNS), deep linking, performance optimization, bundle reduction, app store submission, and cross-platform best practices.
# 文字数: 200+ 文字（簡潔）
```

### 解決策2: 重要なキーワードに絞る

```yaml
description: Mobile development specialist for React Native and Flutter. Use PROACTIVELY for native integrations, offline sync, push notifications, performance optimization, and cross-platform development.
# 文字数: 150+ 文字（最適）
```

### 解決策3: Examples でカバー

```yaml
description: Mobile development specialist. Use PROACTIVELY for React Native and Flutter. Examples: <example>Context: Native feature needed. user: 'Add camera' assistant: 'Using mobile-developer for native integration.' <commentary>Handles platform-specific code.</commentary></example>
# Examples で詳細なシナリオを補完
```

## パターン別テンプレート

### パターン1: シンプルレビュアー型

```yaml
name: simple-reviewer
description: [Role] for [qualities]. Use PROACTIVELY [when/after action] to [goal].
```

**実例**:
```yaml
name: code-reviewer
description: Expert code review specialist for quality, security, and maintainability. Use PROACTIVELY after writing or modifying code to ensure high development standards.
```

### パターン2: ドメイン専門家型

```yaml
name: domain-expert
description: [Domain] specialist for [technology stack]. Use PROACTIVELY for [use case 1], [use case 2], [use case 3], and [general area].
```

**実例**:
```yaml
name: mobile-developer
description: Cross-platform mobile development specialist for React Native and Flutter. Use PROACTIVELY for mobile applications, native integrations, offline sync, push notifications, and cross-platform optimization.
```

### パターン3: MCP/ツール統合型

```yaml
name: tool-specialist
description: [Tool/Service] integration specialist. MUST BE USED for all [scope]-related tasks including [task 1], [task 2], [task 3]. Use PROACTIVELY when working with [context 1], [context 2], or [context 3].
```

**実例**:
```yaml
name: expo-mcp-specialist
description: Expo MCP Server integration specialist. MUST BE USED for all Expo MCP-related tasks including documentation search, library installation, automation testing, and AI-assisted development workflows. Use PROACTIVELY when working with Expo projects, mobile app testing, or AI-powered development automation.
```

### パターン4: 詳細レビュアー型（Examples付き）

```yaml
name: detailed-reviewer
description: [Purpose statement]. Specializes in [expertise areas]. Examples: <example>Context: [scenario 1]. user: '[user request]' assistant: '[agent usage]' <commentary>[rationale]</commentary></example> <example>Context: [scenario 2]. user: '[user request]' assistant: '[agent usage]' <commentary>[rationale]</commentary></example>
```

**実例**:
```yaml
name: architect-reviewer
description: Use this agent to review code for architectural consistency and patterns. Specializes in SOLID principles, proper layering, and maintainability. Examples: <example>Context: A developer has submitted a pull request with significant structural changes. user: 'Please review the architecture of this new feature.' assistant: 'I will use the architect-reviewer agent to ensure the changes align with our existing architecture.' <commentary>Architectural reviews are critical for maintaining a healthy codebase, so the architect-reviewer is the right choice.</commentary></example>
```

## チェックリスト

description を書いたら、以下を確認してください：

- [ ] 「何をするか」が明確
- [ ] 「いつ使うか」が明示されている
- [ ] 具体的なトリガーワード（技術名、タスク名）が3つ以上含まれている
- [ ] `Use PROACTIVELY` または `MUST BE USED` を検討した
- [ ] 1024文字以内に収まっている
- [ ] ユーザーが自然に使う言葉を含んでいる
- [ ] 他のエージェントと役割が重複していない
- [ ] 必要に応じて `<example>` タグを使用した

## 実践例：descriptionの段階的改善

### ステップ1: 最小構成
```yaml
description: Security checker
```

**問題**: いつ使うか不明、トリガーワード不足

### ステップ2: 基本情報追加
```yaml
description: Security vulnerability checker. Use when reviewing code for security issues.
```

**改善**: 使用タイミング追加、でも受動的

### ステップ3: 積極的パターン
```yaml
description: Security auditor for vulnerability detection. Use PROACTIVELY after code changes to check for security issues.
```

**改善**: PROACTIVELY追加、でもキーワード不足

### ステップ4: キーワード拡充
```yaml
description: Security auditor for OWASP vulnerabilities, XSS, SQL injection, CSRF, authentication flaws. Use PROACTIVELY after code changes, especially API endpoints, auth flows, and data validation.
```

**改善**: 具体的な脆弱性タイプ、対象領域明示

### ステップ5: 強制パターン（最終形）
```yaml
description: Security vulnerability auditor. MUST BE USED for all security-sensitive changes including authentication, authorization, API endpoints, data validation, and user input handling. Use PROACTIVELY to detect OWASP Top 10 vulnerabilities, XSS, SQL injection, CSRF, and insecure configurations.
```

**完成**: MUST BE USED、広範なキーワード、明確なスコープ

## よくある間違いと修正

### 間違い1: 曖昧すぎる

```yaml
# ❌ 悪い
description: Helps with development

# ✅ 良い
description: Full-stack development specialist for Node.js, React, and PostgreSQL. Use PROACTIVELY for API development, database design, and frontend implementation.
```

### 間違い2: トリガーワードが少ない

```yaml
# ❌ 悪い
description: Test specialist

# ✅ 良い
description: Test automation specialist for Jest, React Testing Library, E2E testing, unit tests, integration tests, and TDD. Use PROACTIVELY when writing tests, improving coverage, or debugging test failures.
```

### 間違い3: 受動的すぎる

```yaml
# ❌ 悪い
description: Performance optimization specialist. Use when needed.

# ✅ 良い
description: Performance profiler for bottleneck detection, memory leaks, bundle optimization, and load testing. Use PROACTIVELY after implementing new features or when performance issues are suspected.
```

### 間違い4: 長すぎる

```yaml
# ❌ 悪い（450文字）
description: This agent is a comprehensive documentation expert that specializes in creating high-quality technical documentation including API documentation, user guides, README files, architecture decision records, code comments, and inline documentation. It can help with generating OpenAPI specifications, writing clear and concise tutorials, creating getting started guides, and maintaining documentation consistency across the entire project. The agent follows best practices for technical writing and ensures all documentation is up-to-date.

# ✅ 良い（200文字）
description: Technical documentation specialist for API docs, READMEs, ADRs, OpenAPI specs, and user guides. Use PROACTIVELY when documenting features, APIs, or architecture decisions. Ensures clarity, consistency, and up-to-date documentation.
```

---

この descriptionガイドを参考に、エージェントの目的とスコープに応じて最適な記述方法を選択してください。
