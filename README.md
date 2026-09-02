# 🤖 AI Code Reviewer & Bug Fixing Agent

A privacy-first **hybrid multi-agent AI code review system** built with **Streamlit, Ollama, and Qwen2.5-Coder 3B**.

The application analyzes source code using specialized AI agents, performs deterministic syntax/structure validation, generates a corrected version, validates the correction, and generates test cases for review.

> **Safety:** The application does not execute submitted source code. Tests are generated for review only.

---

## ✨ Features

- 🐛 **Bug Detection Agent**
- 🔐 **Security Review Agent**
- ⚡ **Performance Review Agent**
- 📊 **Code Quality Agent**
- 🔧 **Bug Fixing Agent**
- 🧪 **Test Case Agent**
- 🔎 Deterministic syntax/structure pre-check
- 🧠 Local LLM inference through Ollama
- 🎯 AI quality score + deterministic final score
- ❌ Exact syntax error line/column for Python
- 💻 Original vs corrected code comparison
- 🧪 Corrected-code validation without execution
- 📥 Downloadable review report
- 🔧 Download corrected source code
- 🔐 Source code remains local

---

## 🏗️ System Architecture

```text
                         ┌──────────────────────┐
                         │       User Code      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                      ┌─────────────────────────┐
                      │ Deterministic Pre-check │
                      │ AST / Structure Check   │
                      └────────────┬────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
                ▼                  ▼                  ▼
        ┌─────────────┐    ┌─────────────┐    ┌──────────────┐
        │ Bug Agent   │    │Security     │    │ Performance  │
        │             │    │Agent        │    │ Agent        │
        └──────┬──────┘    └──────┬──────┘    └──────┬───────┘
               │                  │                  │
               └──────────────────┼──────────────────┘
                                  ▼
                         ┌─────────────────┐
                         │ Quality Agent   │
                         │ Score /100      │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Bug Fixing      │
                         │ Agent           │
                         └────────┬────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ Corrected Code       │
                       │ Safe Validation      │
                       └──────────┬───────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Test Case Agent │
                         │ Tests NOT RUN   │
                         └─────────────────┘
```

---

## 🧠 Why Hybrid AI?

A pure LLM reviewer can sometimes miss obvious deterministic errors.

This project combines:

### Deterministic validation
For Python, the application uses `ast.parse()` to identify syntax errors without executing the code.

For other supported languages, it performs lightweight structural checks such as delimiter matching.

### AI analysis
The local Qwen2.5-Coder model handles:

- logical bug analysis
- security review
- performance review
- code quality assessment
- correction generation
- test generation

This combination makes the reviewer more reliable than relying on an LLM alone.

---

## 🔐 Safety & Privacy

The application is designed around a **no-source-execution policy**.

The submitted code is:

- parsed/structurally checked where supported
- analyzed by the local model
- used to generate a correction
- used to generate test cases

The application does **not** execute the submitted source code.

All AI inference is performed locally through Ollama.

---

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Application logic |
| Streamlit | Web UI |
| Ollama | Local LLM runtime |
| Qwen2.5-Coder 3B | Code-focused local LLM |
| Python AST | Safe Python syntax validation |
| Regex | Score/result parsing |

---

## 📁 Project Structure

```text
AI-Code-Reviewer/
│
├── app.py
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Install Ollama

Install Ollama for Windows and make sure the Ollama service is running.

### 4. Download the model

```powershell
ollama pull qwen2.5-coder:3b
```

### 5. Verify the model

```powershell
ollama list
```

You should see:

```text
qwen2.5-coder:3b
```

### 6. Start the application

```powershell
streamlit run app.py
```

The Streamlit interface will open in the browser.

---

## 🧪 Demo Test Case

Use this intentionally broken Python code:

```python
def add(a, b)
    return a + b

print(add(5, 10))
```

### Expected behavior

The deterministic pre-check should report:

```text
FAIL
Line 1, column 14: expected ':'
```

The Bug Detection Agent should also receive the confirmed validation issue.

The Bug Fixing Agent should generate a corrected version similar to:

```python
def add(a, b):
    return a + b

print(add(5, 10))
```

The corrected code should pass Python AST validation.

> Exact AI wording and quality score can vary because the local LLM generates the analysis.

---

## 📊 Example Workflow

1. User selects a programming language.
2. User pastes source code.
3. Deterministic validation runs.
4. Bug Agent analyzes bugs.
5. Security Agent analyzes security risks.
6. Performance Agent analyzes efficiency.
7. Quality Agent evaluates quality and produces a score.
8. Bug Fixing Agent generates corrected code.
9. Corrected code is safely validated.
10. Test Agent generates test cases.
11. User can compare original and corrected code.
12. User can download the report and corrected code.

---

## 🎯 Scoring Logic

The application displays:

### AI Score
The score returned by the Quality Agent.

### Final Score
The score used by the dashboard after deterministic validation.

If the original source fails syntax/structure validation, the final score is capped at **50/100** so an invalid program cannot receive an artificially high final score.

If the Quality Agent does not return a machine-readable score, the application uses a conservative deterministic fallback.

---

## 🧪 Testing Policy

The application intentionally does **not** run arbitrary submitted source code.

Therefore:

```text
Test Case Agent → generates tests
Application      → does not execute tests
```

This avoids turning the code-review application into an arbitrary code-execution environment.

---

## 🚀 Future Scope

Possible future improvements include:

- compiler-backed validation in an isolated sandbox
- repository/GitHub integration
- pull-request review
- code diff visualization
- persistent review history
- additional programming languages
- static-analysis integrations
- configurable agent prompts
- CI/CD integration
- containerized deployment

---

## 👨‍💻 Project Goal

The goal of this project is to demonstrate how **Generative AI and deterministic program analysis can work together** to create a practical developer tool.

Instead of asking a single LLM to "review this code", the application uses a **multi-agent workflow** where different agents focus on different software-engineering concerns.

---

## ⚠️ Limitations

- AI-generated analysis may occasionally be incorrect.
- Non-Python validation is lightweight structural validation, not full compiler validation.
- Generated tests are not executed.
- Local model performance depends on available hardware.
- The project is designed as a developer-assistance tool, not a replacement for production static-analysis or security tooling.

---

## 📌 Demo Checklist

Before presenting the project:

- [ ] Ollama is running
- [ ] `qwen2.5-coder:3b` is available
- [ ] `streamlit run app.py` works
- [ ] Editor starts empty
- [ ] Broken Python example detects missing `:`
- [ ] Corrected code passes validation
- [ ] Six agent stages complete
- [ ] AI Score is displayed
- [ ] Final Score is displayed
- [ ] Test Cases are generated
- [ ] Full report downloads
- [ ] Corrected code downloads

---

## 📄 License

This project is intended as an educational/internship build-sprint project.
