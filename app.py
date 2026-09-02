
import ast
import re
from datetime import datetime

import ollama
import streamlit as st


# ============================================================
# AI CODE REVIEWER & BUG FIXING AGENT - FINAL UI V7
# Local LLM: Ollama + Qwen2.5-Coder 3B
#
# IMPORTANT:
# This application NEVER executes user source code.
# It performs deterministic syntax/structure validation plus
# local LLM-based analysis and fix generation.
# ============================================================

MODEL = "qwen2.5-coder:3b"

st.set_page_config(
    page_title="AI Code Reviewer",
    page_icon="🤖",
    layout="wide",
)

st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.55rem;
        font-weight: 800;
        margin-bottom: 0.15rem;
    }
    .subtitle {
        color: #9aa4b2;
        font-size: 1.03rem;
        margin-bottom: 1rem;
    }
    .hero {
        padding: 1.25rem 1.4rem;
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 16px;
        background: linear-gradient(135deg, rgba(30,41,59,0.72), rgba(15,23,42,0.72));
        margin-bottom: 1.2rem;
    }
    .hero-badge {
        display: inline-block;
        padding: 0.25rem 0.62rem;
        border-radius: 999px;
        border: 1px solid rgba(255,255,255,0.14);
        font-size: 0.76rem;
        margin-right: 0.3rem;
    }
    .pipeline-card {
        text-align: center;
        padding: 0.65rem 0.2rem;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,0.2);
        background: rgba(30,41,59,0.42);
        min-height: 72px;
    }
    .pipeline-icon {
        font-size: 1.3rem;
    }
    .pipeline-name {
        font-size: 0.8rem;
        font-weight: 700;
        margin-top: 0.15rem;
    }
    .small-muted {
        color: #8b95a5;
        font-size: 0.78rem;
    }
    .score-note {
        padding: 0.65rem 0.85rem;
        border-radius: 10px;
        border: 1px solid rgba(128,128,128,0.2);
        background: rgba(30,41,59,0.35);
        margin-top: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# BASIC HELPERS
# ============================================================

def call_ollama(system_prompt: str, user_prompt: str) -> str:
    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": 0.1},
    )
    return response["message"]["content"]


def run_agent(agent_name: str, code: str, language: str, context: str = "") -> str:
    system_prompt = f"""
You are the {agent_name} in a multi-agent AI Code Review system.

Programming language: {language}

Rules:
1. Analyze the supplied code carefully.
2. Be concise and technically accurate.
3. Do not invent errors.
4. Preserve original function names, variable names, class names,
   and intended functionality whenever possible.
5. If no issue is found in your category, say:
   "No major issue found."
6. Never claim that code was executed or tested.
7. This application does not execute user source code.
8. Use clear headings and bullet points.
"""

    user_prompt = f"""
Review the following code as the {agent_name}.

--- CODE START ---
{code}
--- CODE END ---

Additional deterministic validation information:
{context}

Return findings specifically for your role.
"""

    return call_ollama(system_prompt, user_prompt)


def parse_score(text: str):
    """Extract a 0-100 score from common LLM formats."""
    if not text:
        return None

    patterns = [
        r"\bSCORE\s*:\s*(\d{1,3})(?:\s*/\s*100)?",
        r"\bQUALITY\s+SCORE\s*[:\-]?\s*(\d{1,3})(?:\s*/\s*100)?",
        r"\bFINAL\s+SCORE\s*[:\-]?\s*(\d{1,3})(?:\s*/\s*100)?",
        r"\bSCORE\s*(?:IS|=|-)\s*(\d{1,3})(?:\s*/\s*100)?",
        r"\b(\d{1,3})\s*/\s*100\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if 0 <= value <= 100:
                return value

    return None


def fallback_score(validation_ok, bug_report, security_report, performance_report):
    """Conservative deterministic fallback if the AI score is missing."""
    if not validation_ok:
        return 40

    combined = (
        f"{bug_report}\n{security_report}\n{performance_report}"
    ).lower()

    severe_terms = [
        "critical",
        "high severity",
        "major bug",
        "security vulnerability",
        "unsafe",
    ]
    issue_terms = [
        "bug",
        "error",
        "issue",
        "vulnerability",
        "inefficient",
        "performance problem",
    ]

    severe_count = sum(combined.count(term) for term in severe_terms)
    issue_count = sum(combined.count(term) for term in issue_terms)

    score = 90
    score -= min(severe_count * 8, 24)
    score -= min(max(issue_count - 2, 0) * 3, 18)

    return max(50, min(100, score))


def calculate_final_score(ai_score, validation_ok, fallback):
    """Apply deterministic validation to the selected score."""
    score = ai_score if ai_score is not None else fallback

    if not validation_ok:
        return min(score, 50)

    return score


def clean_code_block(text: str) -> str:
    blocks = re.findall(
        r"```(?:[A-Za-z0-9_+#.-]+)?\s*\n?(.*?)```",
        text,
        re.DOTALL,
    )
    if blocks:
        return blocks[-1].strip()
    return text.strip()


# ============================================================
# DETERMINISTIC VALIDATION
# ============================================================

def validate_python(code: str):
    """
    Python validation using AST.
    The source code is parsed but NEVER executed.
    """
    try:
        ast.parse(code)
        return True, "Python syntax is valid (AST parse passed).", None
    except SyntaxError as exc:
        line = exc.lineno if exc.lineno is not None else "?"
        column = exc.offset if exc.offset is not None else "?"
        message = exc.msg or "Syntax error"

        detail = {
            "line": line,
            "column": column,
            "message": message,
        }

        return (
            False,
            f"Line {line}, column {column}: {message}",
            detail,
        )


def validate_generic_structure(code: str):
    """
    Lightweight structural validation for non-Python languages.
    This is NOT a compiler/interpreter and does NOT execute code.
    """
    pairs = {"(": ")", "[": "]", "{": "}"}
    opening = set(pairs.keys())
    closing = set(pairs.values())

    stack = []

    in_single = False
    in_double = False
    in_backtick = False
    escape = False

    for char in code:
        if escape:
            escape = False
            continue

        if char == "\\" and (in_single or in_double or in_backtick):
            escape = True
            continue

        if char == "'" and not in_double and not in_backtick:
            in_single = not in_single
            continue

        if char == '"' and not in_single and not in_backtick:
            in_double = not in_double
            continue

        if char == "`" and not in_single and not in_double:
            in_backtick = not in_backtick
            continue

        if in_single or in_double or in_backtick:
            continue

        if char in opening:
            stack.append(char)

        elif char in closing:
            if not stack:
                return False, f"Unexpected closing delimiter: {char}", None

            expected = pairs[stack[-1]]

            if expected != char:
                return (
                    False,
                    f"Mismatched delimiter: expected {expected}, found {char}",
                    None,
                )

            stack.pop()

    if in_single or in_double or in_backtick:
        return False, "Unclosed string/template literal detected.", None

    if stack:
        return False, f"Unclosed delimiter: {stack[-1]}", None

    return True, "Basic structural validation passed.", None


def validate_code(code: str, language: str):
    if not code.strip():
        return False, "No code was supplied.", None

    if language.lower() == "python":
        return validate_python(code)

    return validate_generic_structure(code)


def validation_context(ok: bool, message: str):
    if ok:
        return f"""
DETERMINISTIC PRE-CHECK: PASS
{message}

The source passed the available syntax/structure check.
Still inspect the code for logical, security, and performance issues.
"""

    return f"""
DETERMINISTIC PRE-CHECK: FAIL
{message}

This is a confirmed validation problem.
The AI bug analysis MUST mention this issue clearly.
Do not say the code is syntactically correct.
"""


# ============================================================
# AI FIXER
# ============================================================

def generate_fixed_code(code: str, language: str, review_context: str) -> str:
    system_prompt = f"""
You are the Bug Fixing Agent.

Programming language: {language}

Your job is to return a corrected COMPLETE version of the source code.

Strict rules:
1. Fix confirmed syntax/structure problems first.
2. Fix relevant bugs identified by the review.
3. Preserve original identifiers whenever possible.
4. Preserve intended functionality.
5. Do not rename functions or variables just for style.
6. Do not add unrelated features.
7. Return the COMPLETE source code.
8. Put it inside exactly ONE fenced code block.
9. Never claim that the code was executed.
"""

    user_prompt = f"""
Original code:
--- CODE START ---
{code}
--- CODE END ---

Review and deterministic validation:
{review_context}

Produce the corrected complete source code.
"""

    result = call_ollama(system_prompt, user_prompt)
    return clean_code_block(result)


# ============================================================
# TEST GENERATOR
# ============================================================

def generate_tests(code: str, language: str) -> str:
    system_prompt = f"""
You are the Test Case Agent.

Programming language: {language}

Generate useful test cases for the supplied code.

Rules:
1. Generate tests only; DO NOT execute them.
2. Never claim a test passed or failed.
3. Never fabricate execution output.
4. Cover normal cases, boundary cases, and edge cases.
5. Preserve original identifiers.
"""

    user_prompt = f"""
Generate test cases for:

--- CODE START ---
{code}
--- CODE END ---

Include:
- Test objective
- Test cases
- Expected result
- Optional test code

End exactly with:
EXECUTION STATUS: NOT RUN
"""

    return call_ollama(system_prompt, user_prompt)


# ============================================================
# REPORT
# ============================================================

def build_report(
    language,
    original_code,
    original_validation_ok,
    original_validation_message,
    score,
    score_source,
    final_score,
    bug_report,
    security_report,
    performance_report,
    quality_report,
    fixed_code,
    fixed_validation_ok,
    fixed_validation_message,
    tests,
):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    score_text = str(score) if score is not None else "N/A"
    original_status = "PASS" if original_validation_ok else "FAIL"
    fixed_status = "PASS" if fixed_validation_ok else "FAIL"

    return f"""AI CODE REVIEWER REPORT
========================

Generated: {timestamp}
Language: {language}
Model: {MODEL}

EXECUTION POLICY
----------------
User source code is NEVER executed by this application.

ORIGINAL CODE VALIDATION
------------------------
Status: {original_status}
{original_validation_message}

AI CODE QUALITY SCORE
---------------------
{score_text}/100
Source: {score_source}

FINAL SCORE
-----------
{final_score if final_score is not None else "N/A"}/100

BUG DETECTION
-------------
{bug_report}

SECURITY REVIEW
---------------
{security_report}

PERFORMANCE REVIEW
------------------
{performance_report}

QUALITY REVIEW
--------------
{quality_report}

CORRECTED CODE
--------------
{fixed_code}

CORRECTED CODE VALIDATION
-------------------------
Status: {fixed_status}
{fixed_validation_message}

TEST CASES
----------
{tests}

IMPORTANT
---------
Tests are generated for review only.
Source code is not executed by the application.
"""


# ============================================================
# UI
# ============================================================

st.markdown(
    '<div class="main-title">🤖 AI Code Reviewer & Bug Fixing Agent</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="subtitle">Privacy-first hybrid multi-agent code review, fixing, validation, and test generation.</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
        <div style="color:#8b95a5; font-size:0.76rem; letter-spacing:0.08em; font-weight:700;">
            LOCAL AI DEVELOPMENT TOOL
        </div>
        <h3 style="margin:0.2rem 0 0.5rem 0;">
            AI analysis backed by deterministic validation
        </h3>
        <p style="margin:0 0 0.75rem 0; color:#b7c0cc;">
            Six specialized agents find issues, explain them, generate a fix,
            validate the correction, and prepare test cases — without executing your code.
        </p>
        <span class="hero-badge">🤖 Qwen2.5-Coder 3B</span>
        <span class="hero-badge">🦙 Ollama</span>
        <span class="hero-badge">🔐 Local / Private</span>
        <span class="hero-badge">🛡️ Safe Validation</span>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ Settings")

    language = st.selectbox(
        "Programming Language",
        [
            "Python",
            "Java",
            "C++",
            "C",
            "JavaScript",
            "SQL",
        ],
    )

    st.markdown("---")

    st.subheader("🧠 AI Model")
    st.write(f"**{MODEL}**")
    st.caption("Runs locally through Ollama")

    st.subheader("🔐 Privacy")
    st.success("Your source code stays on your machine.")

    st.subheader("🛡️ Safe Validation")
    st.info(
        "Syntax/structure is checked without executing your source code."
    )

    if st.button(
        "🗑️ Clear Review",
        use_container_width=True,
        key="clear_review",
    ):
        st.session_state.review_results = None
        st.session_state.code_input = ""
        st.rerun()


EXAMPLE_CODE = {
    "Python": """def add(a, b)
    return a + b

print(add(5, 10))
""",
    "Java": """public class Main {
    public static void main(String[] args) {
        int a = 10;
        int b = 20
        System.out.println(a + b);
    }
}
""",
    "C++": """#include <iostream>
using namespace std;

int main() {
    int a = 10;
    int b = 20
    cout << a + b << endl;
    return 0;
}
""",
    "C": """#include <stdio.h>

int main() {
    int a = 10;
    int b = 20
    printf("%d", a + b);
    return 0;
}
""",
    "JavaScript": """function add(a, b) {
    return a + b
}

console.log(add(5, 10);
""",
    "SQL": """SELECT name, email
FROM users
WHERE age > 18
ORDER BY name;
""",
}


if "last_language" not in st.session_state:
    st.session_state.last_language = language

if "code_input" not in st.session_state:
    st.session_state.code_input = ""

if language != st.session_state.last_language:
    # Do not inject built-in code into the editor.
    # The user can use "Load Example" whenever they want.
    st.session_state.code_input = ""
    st.session_state.last_language = language


st.markdown("### 💻 Code Workspace")
st.caption(
    "Paste your source code, choose the language from the sidebar, and start the review."
)

code = st.text_area(
    "Source code",
    key="code_input",
    height=320,
    label_visibility="collapsed",
    placeholder=(
        "Paste your source code here...\n\n"
        "Example:\n"
        "def add(a, b):\n"
        "    return a + b"
    ),
)

col1, col2, col3 = st.columns([1.1, 1.1, 0.8])

with col1:
    review_clicked = st.button(
        "🚀 Review Code",
        type="primary",
        use_container_width=True,
        key="review_code",
    )

with col2:
    example_clicked = st.button(
        "🧪 Load Example Code",
        use_container_width=True,
        key="load_example",
    )

with col3:
    st.markdown(
        '<div class="small-muted" style="padding-top:0.55rem;">'
        'No source execution<br>100% local processing'
        '</div>',
        unsafe_allow_html=True,
    )

if example_clicked:
    st.session_state.code_input = EXAMPLE_CODE[language]
    st.rerun()

if not code.strip():
    st.caption(
        "💡 The editor is intentionally empty. Paste your own code, "
        "or click **Load Example Code** to try the demo."
    )

with st.expander("ℹ️ How the review works", expanded=False):
    st.markdown(
        """
        **1. Deterministic pre-check** → catches confirmed syntax/structure problems.  
        **2. AI agents** → bugs, security, performance, and quality analysis.  
        **3. Bug Fixing Agent** → generates a complete corrected version.  
        **4. Safe validation** → validates the correction without executing it.  
        **5. Test Case Agent** → generates tests for review; tests are not run.
        """
    )


# ============================================================
# REVIEW WORKFLOW
# ============================================================

if review_clicked:
    if not code.strip():
        st.warning("Please enter some code first.")
        st.stop()

    st.session_state.review_results = None

    progress = st.progress(0)
    status = st.empty()

    try:
        # ----------------------------------------------------
        # STEP 1: Deterministic pre-check
        # ----------------------------------------------------
        status.info("🔎 Running deterministic syntax/structure pre-check...")

        original_validation_ok, original_validation_message, original_detail = (
            validate_code(code, language)
        )

        progress.progress(10)

        precheck = validation_context(
            original_validation_ok,
            original_validation_message,
        )

        # ----------------------------------------------------
        # STEP 2: Bug Agent
        # ----------------------------------------------------
        status.info("🐛 Bug Detection Agent is reviewing...")

        bug_report = run_agent(
            "Bug Detection Agent",
            code,
            language,
            precheck
            + """
Focus on syntax errors, logic errors, incorrect behavior,
edge cases, and the deterministic pre-check result.
""",
        )

        # Force confirmed syntax error into the displayed bug report
        # so an LLM cannot accidentally hide a deterministic finding.
        if not original_validation_ok:
            bug_report = (
                "### ⚠️ Confirmed Validation Issue\n\n"
                f"- {original_validation_message}\n\n"
                + bug_report
            )

        progress.progress(25)

        # ----------------------------------------------------
        # STEP 3: Security Agent
        # ----------------------------------------------------
        status.info("🔐 Security Agent is reviewing...")

        security_report = run_agent(
            "Security Agent",
            code,
            language,
            precheck
            + """
Focus on injection, unsafe input handling, secrets,
authentication/authorization mistakes, unsafe APIs,
and data exposure.
""",
        )

        progress.progress(40)

        # ----------------------------------------------------
        # STEP 4: Performance Agent
        # ----------------------------------------------------
        status.info("⚡ Performance Agent is reviewing...")

        performance_report = run_agent(
            "Performance Agent",
            code,
            language,
            precheck
            + """
Focus on time complexity, space complexity,
unnecessary work, scalability, and resource usage.
""",
        )

        progress.progress(55)

        # ----------------------------------------------------
        # STEP 5: Quality Agent
        # ----------------------------------------------------
        status.info("📊 Quality Agent is scoring the code...")

        quality_report = run_agent(
            "Quality Agent",
            code,
            language,
            precheck
            + """
Give a final code quality assessment.

At the end include exactly:
SCORE: [number between 0 and 100]
""",
        )

        score = parse_score(quality_report)

        if score is None:
            score = fallback_score(
                original_validation_ok,
                bug_report,
                security_report,
                performance_report,
            )
            score_source = "Deterministic fallback"
        else:
            score_source = "AI Quality Agent"

        final_score = calculate_final_score(
            score,
            original_validation_ok,
            score,
        )

        progress.progress(65)

        # ----------------------------------------------------
        # STEP 6: Fixer Agent
        # ----------------------------------------------------
        status.info("🔧 Bug Fixing Agent is generating a correction...")

        combined_review = (
            f"DETERMINISTIC VALIDATION:\n{precheck}\n\n"
            f"BUG REPORT:\n{bug_report}\n\n"
            f"SECURITY REPORT:\n{security_report}\n\n"
            f"PERFORMANCE REPORT:\n{performance_report}\n\n"
            f"QUALITY REPORT:\n{quality_report}"
        )

        fixed_code = generate_fixed_code(
            code,
            language,
            combined_review,
        )

        progress.progress(78)

        # ----------------------------------------------------
        # STEP 7: Validate corrected code
        # ----------------------------------------------------
        status.info("🧪 Validating corrected code safely...")

        fixed_validation_ok, fixed_validation_message, fixed_detail = (
            validate_code(fixed_code, language)
        )

        progress.progress(88)

        # ----------------------------------------------------
        # STEP 8: Test Agent
        # ----------------------------------------------------
        status.info("🧪 Test Case Agent is generating tests...")

        tests = generate_tests(
            fixed_code,
            language,
        )

        progress.progress(100)
        status.success("✅ Hybrid multi-agent review completed.")

        st.session_state.review_results = {
            "original_validation_ok": original_validation_ok,
            "original_validation_message": original_validation_message,
            "original_detail": original_detail,
            "bug_report": bug_report,
            "security_report": security_report,
            "performance_report": performance_report,
            "quality_report": quality_report,
            "score": score,
            "score_source": score_source,
            "final_score": final_score,
            "fixed_code": fixed_code,
            "fixed_validation_ok": fixed_validation_ok,
            "fixed_validation_message": fixed_validation_message,
            "fixed_detail": fixed_detail,
            "tests": tests,
        }

    except Exception as exc:
        progress.empty()
        status.empty()

        st.error(
            "Could not complete the review. Make sure Ollama is running "
            f"and '{MODEL}' is available."
        )
        st.exception(exc)


# ============================================================
# RESULTS DASHBOARD
# ============================================================

results = st.session_state.get("review_results")

if results:
    st.markdown("---")
    st.header("📋 Review Dashboard")

    original_ok = results["original_validation_ok"]
    fixed_ok = results["fixed_validation_ok"]
    ai_score = results["score"]
    final_score = results["final_score"]

    # --------------------------------------------------------
    # Summary cards
    # --------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if final_score is not None:
            st.metric("🎯 Final Score", f"{final_score}/100")
        else:
            st.metric("🎯 Final Score", "N/A")

    with c2:
        if ai_score is not None:
            st.metric("🤖 AI Score", f"{ai_score}/100")
        else:
            st.metric("🤖 AI Score", "N/A")

    with c3:
        st.metric(
            "🔎 Original Check",
            "PASS" if original_ok else "FAIL",
        )

    with c4:
        st.metric(
            "🔧 Fixed Check",
            "PASS" if fixed_ok else "FAIL",
        )

    # --------------------------------------------------------
    # Score explanation
    # --------------------------------------------------------
    if final_score is not None:
        st.progress(final_score / 100)

    st.markdown(
        f'<div class="score-note"><b>Score source:</b> '
        f'{results["score_source"]} &nbsp;•&nbsp; '
        f'<b>Rule:</b> invalid original code is capped at 50/100.</div>',
        unsafe_allow_html=True,
    )

    if results["score_source"] == "Deterministic fallback":
        st.info(
            "ℹ️ The Quality Agent did not return a machine-readable score, "
            "so the app used a conservative deterministic fallback score."
        )

    if not original_ok:
        st.warning(
            f"⚠️ Deterministic validation found a confirmed syntax/structure "
            f"problem. The final score is capped at {final_score}/100."
        )
    else:
        st.success(
            "✅ The original code passed deterministic syntax/structure validation."
        )

    # --------------------------------------------------------
    # Confirmed validation issue
    # --------------------------------------------------------
    if not original_ok:
        st.subheader("❌ Confirmed Issue")

        st.error(
            f"**{results['original_validation_message']}**"
        )

        if results.get("original_detail"):
            detail = results["original_detail"]
            if detail:
                d1, d2, d3 = st.columns(3)
                with d1:
                    st.write(f"**Line:** {detail.get('line', '?')}")
                with d2:
                    st.write(f"**Column:** {detail.get('column', '?')}")
                with d3:
                    st.write(f"**Message:** {detail.get('message', 'Syntax error')}")

    # --------------------------------------------------------
    # Agent status row
    # --------------------------------------------------------
    st.subheader("🤖 Agent Pipeline")

    pipeline = [
        ("🐛", "Bug Detection"),
        ("🔐", "Security"),
        ("⚡", "Performance"),
        ("📊", "Quality"),
        ("🔧", "Bug Fix"),
        ("🧪", "Test Cases"),
    ]

    pipeline_cols = st.columns(6)

    for pipeline_col, item in zip(pipeline_cols, pipeline):
        icon, name = item
        with pipeline_col:
            st.markdown(
                f'<div class="pipeline-card">'
                f'<div class="pipeline-icon">{icon}</div>'
                f'<div class="pipeline-name">{name}</div>'
                f'<div class="small-muted">Completed</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # --------------------------------------------------------
    # Original code + corrected code comparison
    # --------------------------------------------------------
    st.subheader("💻 Code Comparison")

    left, right = st.columns(2)

    with left:
        st.markdown("### 📄 Original Code")
        st.code(
            code,
            language=language.lower(),
        )

        if original_ok:
            st.success("Original validation: PASS")
        else:
            st.error("Original validation: FAIL")

    with right:
        st.markdown("### 🔧 Corrected Code")
        st.code(
            results["fixed_code"],
            language=language.lower(),
        )

        if fixed_ok:
            st.success("Corrected validation: PASS")
        else:
            st.error("Corrected validation: FAIL")

    # --------------------------------------------------------
    # Detailed agent reports
    # --------------------------------------------------------
    st.subheader("🔍 Detailed Agent Reports")

    tabs = st.tabs(
        [
            "🐛 Bugs",
            "🔐 Security",
            "⚡ Performance",
            "📊 Quality",
            "🔧 Fix Details",
            "🧪 Test Cases",
        ]
    )

    with tabs[0]:
        if not original_ok:
            st.error(
                f"Confirmed deterministic issue: "
                f"{results['original_validation_message']}"
            )
        st.markdown(results["bug_report"])

    with tabs[1]:
        st.markdown(results["security_report"])

    with tabs[2]:
        st.markdown(results["performance_report"])

    with tabs[3]:
        st.caption(f"Score source: {results['score_source']}")
        st.markdown(results["quality_report"])

    with tabs[4]:
        st.markdown(
            "The Bug Fixing Agent generated the corrected source below."
        )
        st.code(
            results["fixed_code"],
            language=language.lower(),
        )
        st.markdown(
            f"**Validation:** "
            f"{'PASS' if fixed_ok else 'FAIL'} — "
            f"{results['fixed_validation_message']}"
        )

    with tabs[5]:
        st.markdown(results["tests"])
        st.info(
            "Tests are generated for review only. "
            "Source code is not executed by the application."
        )

    # --------------------------------------------------------
    # Download report
    # --------------------------------------------------------
    report = build_report(
        language=language,
        original_code=code,
        original_validation_ok=results["original_validation_ok"],
        original_validation_message=results["original_validation_message"],
        score=ai_score,
        score_source=results["score_source"],
        final_score=final_score,
        bug_report=results["bug_report"],
        security_report=results["security_report"],
        performance_report=results["performance_report"],
        quality_report=results["quality_report"],
        fixed_code=results["fixed_code"],
        fixed_validation_ok=results["fixed_validation_ok"],
        fixed_validation_message=results["fixed_validation_message"],
        tests=results["tests"],
    )

    st.markdown("---")
    st.subheader("📥 Download Report")

    d1, d2 = st.columns(2)

    with d1:
        st.download_button(
            "⬇️ Download Full Review Report",
            data=report,
            file_name="ai_code_review_report.txt",
            mime="text/plain",
            use_container_width=True,
            key="download_report",
        )

    extension_map = {
        "Python": "py",
        "Java": "java",
        "C++": "cpp",
        "C": "c",
        "JavaScript": "js",
        "SQL": "sql",
    }

    with d2:
        st.download_button(
            "🔧 Download Corrected Code",
            data=results["fixed_code"],
            file_name=f"corrected_code.{extension_map[language]}",
            mime="text/plain",
            use_container_width=True,
            key="download_fixed_code",
        )

