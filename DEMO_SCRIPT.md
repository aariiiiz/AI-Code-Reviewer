# Demo Script — AI Code Reviewer & Bug Fixing Agent

## 60–90 Second Demo

### 1. Introduce
"This is an AI Code Reviewer and Bug Fixing Agent built using a hybrid multi-agent architecture."

### 2. Show the blank editor
"The editor starts empty so the user can submit their own source code."

### 3. Paste the intentionally broken code

```python
def add(a, b)
    return a + b

print(add(5, 10))
```

### 4. Click Review Code

Explain:

- "First, a deterministic pre-check validates the source."
- "Then specialized AI agents review bugs, security, performance, and quality."
- "A separate agent generates the fix."
- "The corrected code is validated again."
- "Finally, a test-case agent generates tests without executing the source."

### 5. Highlight the confirmed issue

Expected:

```text
Line 1, column 14: expected ':'
```

### 6. Show the corrected code

Point out that the missing colon is repaired while the original function name and intended behavior are preserved.

### 7. Show the score

Explain:

"The AI score and final score are separate. If deterministic validation finds invalid syntax, the final score is capped so the dashboard cannot hide a confirmed syntax problem."

### 8. Show Test Cases

"Tests are generated for review, but the application deliberately does not execute arbitrary user source code."

### 9. Close

"The key idea is combining deterministic program validation with multiple local AI agents to make code review more reliable and privacy-friendly."
