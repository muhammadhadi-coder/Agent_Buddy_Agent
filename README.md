# Study Buddy (OpenAI Agents SDK)

A multi-agent technical tutor built with the **OpenAI Agents SDK** and backed by Google Gemini (`gemini-2.5-flash`). It quizzes you on technical course topics, adapts questions to your profile, remembers your weak spots across sessions, and grades your answers using specialized sub-agents.

---

## Architecture Overview

```
                      +-------------------+
                      |   Student (CLI)   |
                      +---------+---------+
                                |
                                v
                      +-------------------+
                      |    Tutor Agent    | (Study Buddy)
                      +----+---------+----+
                           |         |
          +----------------+         +----------------+
          v                                           v
+-------------------+                       +-------------------+
|  question_writer  | (as_tool, temp 0.9)   |      grader       | (as_tool, temp 0.1, cap)
+-------------------+                       +-------------------+
          |                                           |
          +------------------+     +------------------+
                             |     |
                             v     v
                      +-------------------+
                      |   record_answer   | -> student_profile.json
                      +-------------------+
```

- **Tutor Agent**: Maintains the conversation, tracks profile context, decides which topics need practice, and presents questions and feedback.
- **Question Writer (`as_tool`)**: Specialist agent with high entropy (`temperature=0.9`) that outputs strictly one focused quiz question per run.
- **Grader (`as_tool`)**: Specialist agent with low entropy (`temperature=0.1`) and `max_tokens=100` ceiling that receives the question, student answer, and key facts to return a verdict (`CORRECT`/`INCORRECT`) and one sentence of feedback.
- **Profile Persistence**: Tracks questions answered, accuracy rate, and weak topics in `student_profile.json` across sessions.

---

## Setup Steps

### 1. Prerequisites
- Python 3.10+ (or [uv](https://docs.astral.sh/uv/))
- A Gemini API Key from [Google AI Studio](https://aistudio.google.com/)
- *(Optional)* An OpenAI API Key for tracing exports at [platform.openai.com/traces](https://platform.openai.com/traces)

### 2. Installation

Clone or open the project folder:
```bash
cd study-buddy
```

Using `uv` (recommended):
```bash
uv sync
```

Or using standard `pip`:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install openai-agents python-dotenv
```

### 3. Environment Configuration

Create a `.env` file in the `study-buddy` directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional: for tracing dashboard
```

Make sure `.env` is ignored by Git:
```bash
echo .env >> .gitignore
```

### 4. Run the CLI Loop

```bash
uv run python main.py
```
*(or `.venv/bin/python main.py` / `python main.py`)*

---

## Example Run

Below is a complete transcript from an interactive CLI session:

```text
====================================================================
🤖 Welcome to the OpenAI Agents SDK Study Buddy!
====================================================================
Loaded existing profile for Ada (Level: beginner).
History: 1 topic(s) quizzed previously.

----------------------------------------
MAIN MENU
----------------------------------------
1. Pick a topic to drill
2. Let tutor pick (prioritizes weak topics)
3. View session summary
q. Quit session
----------------------------------------
Select an option [1/2/3/q]: 1

Available Topics:
   1. Agent Foundations (agent-foundations) [Score: 1/1 (100%)]
   2. Setup and Installation (setup-and-installation)
   3. Running Agents and RunResult (running-agents)
   4. Instructions and Personas (instructions-and-personas)
   5. Function Tools (function-tools)
   6. Structured Outputs (structured-outputs)
   7. Handoffs (handoffs)
   8. Guardrails (guardrails)
   9. Sessions and Conversation Memory (sessions-and-memory)
  10. Streaming (streaming)
  11. Tracing and Observability (tracing)
  12. Models and Providers (models-and-providers)
  13. Multi-Agent Orchestration (multi-agent-orchestration)
  14. MCP and Deployment (mcp-and-deployment)

Enter topic number (1-14) or topic ID: 5

[Tutor is consulting notes and generating a question on 'function-tools'...]

====================================================================
📝 TUTOR'S QUESTION
====================================================================
How does the `@function_tool` decorator determine the tool name, description,
and JSON schema for the model to use?
====================================================================

Enter your answer below (or type 'skip' to skip):
> It derives the tool name, description, and schema directly from the Python function's signature, docstring, and type hints.

[Tutor is evaluating your answer with the grader and updating your profile...]

====================================================================
🎯 VERDICT & FEEDBACK
====================================================================
CORRECT: The student correctly identified that the function signature,
docstring, and type hints are used to derive the tool's schema and details.
====================================================================

----------------------------------------
MAIN MENU
----------------------------------------
1. Pick a topic to drill
2. Let tutor pick (prioritizes weak topics)
3. View session summary
q. Quit session
----------------------------------------
Select an option [1/2/3/q]: q

====================================================================
🎓 SESSION SUMMARY FOR ADA (BEGINNER)
====================================================================
Topic ID                       Accuracy     Score      Status
--------------------------------------------------------------------
agent-foundations              100.0%       1/1        Mastered (>70%)
function-tools                 100.0%       1/1        Mastered (>70%)
--------------------------------------------------------------------
Total Questions Answered: 2
Overall Accuracy:        100.0% (2/2)
Weak topics:             None recorded! Keep up the good work!

[Saved] Profile persisted to: student_profile.json
====================================================================

Thanks for studying! Goodbye!
```

---

## What the Agent Does Badly

Honest observations and failure modes discovered during profiling and testing:

1. **Multi-Agent Latency Overhead**:
   Because the tutor delegates question generation and grading to specialist agents through the `as_tool` sub-routine pattern, a single question-and-answer cycle requires **up to 5 sequential network roundtrips**:
   1. Tutor LLM call (decides to call `get_notes`)
   2. Tutor LLM call (decides to call `question_writer`)
   3. `question_writer` LLM call (generates question)
   4. Tutor LLM call (relays question to user)
   5. Tutor LLM call (calls `grader` and `record_answer`)
   6. `grader` LLM call (evaluates answer)
   7. Tutor LLM call (relays feedback)
   This creates a noticeable 4–7 second delay between submitting an answer and seeing feedback.

2. **Redundant "Echo" Model Turn**:
   In Turn 1, the `question_writer` agent outputs a complete, well-formed question. The tutor agent then spends another full model call simply repeating that exact text to the student. Without `tool_use_behavior="stop_on_first_tool"` or custom output extractors, this extra model call burns tokens and adds unnecessary latency.

3. **Rigid Key-Fact Grading**:
   The `grader` evaluates answers strictly against the two `key_facts` recorded in `topics.json`. If a student provides an answer that is technically true in real-world SDK usage but phrased differently or focusing on a detail outside those two bullets, the grader can grade the answer as `INCORRECT`. It lacks nuance when grading open-ended technical answers.

4. **Primitive File Persistence**:
   The `StudentProfile` is serialized as flat JSON in `student_profile.json`. There are no file locks or schema migrations. If multiple CLI sessions run simultaneously or if the JSON file is edited with invalid syntax, the application falls back to a clean profile and can overwrite progress.

5. **Accumulating Context Without Compaction**:
   The CLI app passes the full message history (`result.to_input_list()`) across turns. During long study sessions, previous questions, notes, and tool inputs remain in context, driving up token costs and eventually risking context-window limits without session trimming or summarization.
