# 🤖 Study Buddy — AI-Powered Technical Tutor

**Learn smarter. Practice consistently. Improve with AI. 🚀**

Study Buddy is a multi-agent technical tutor built with the **OpenAI Agents SDK** and powered by **Google Gemini (`gemini-2.5-flash`)**.

It quizzes students on technical topics, adapts questions to their learning profile, tracks weak areas across sessions, and evaluates answers using specialized AI agents.

Whether you're learning Python, AI agents, or the OpenAI Agents SDK, Study Buddy helps you turn passive reading into active learning. 📚

---

## ✨ Key Features

- 🧠 **AI-Powered Tutoring:** An intelligent tutor manages the learning conversation and selects relevant topics.
- 📝 **Dynamic Quiz Generation:** A specialized question-writing agent generates one focused question per run.
- 🎯 **Automated Answer Grading:** A dedicated grading agent evaluates answers and provides concise feedback.
- 📊 **Personalized Learning:** Tracks accuracy and weak topics to help prioritize future practice.
- 💾 **Persistent Student Profiles:** Saves learning progress in `student_profile.json` across sessions.
- 🔄 **Multi-Agent Architecture:** Uses specialist agents as tools to separate question generation and grading from the main tutor.
- 🖥️ **Interactive CLI:** Study directly from your terminal without needing a graphical interface.
- ⚡ **Lightweight Workflow:** Uses Python and Gemini to make AI-assisted study accessible.

---

## 🏗️ Architecture Overview

Study Buddy uses a main tutor agent that coordinates specialized agents and a function tool for recording student progress.

```text
                      +-------------------+
                      |   👨‍🎓 Student CLI   |
                      +---------+---------+
                                |
                                v
                      +-------------------+
                      |   🤖 Tutor Agent  |
                      |    Study Buddy    |
                      +----+---------+----+
                           |         |
               +-----------+         +-----------+
               v                                 v
    +---------------------+          +---------------------+
    |  ✍️ question_writer  |          |    🎯 grader        |
    |      as_tool        |          |      as_tool        |
    |   Temperature: 0.9  |          |   Temperature: 0.1  |
    +----------+----------+          +----------+----------+
               |                                |
               +----------------+---------------+
                                |
                                v
                      +-------------------+
                      | 🗂️ record_answer  |
                      |  Student Profile  |
                      +---------+---------+
                                |
                                v
                      +-------------------+
                      | student_profile   |
                      |      .json        |
                      +-------------------+
```

### 🧩 Agent Responsibilities

| Component | Responsibility |
|---|---|
| 🤖 **Tutor Agent** | Maintains the conversation, uses profile context, selects topics, and presents questions and feedback. |
| ✍️ **Question Writer** | Generates one focused quiz question per run. Uses a higher temperature (`0.9`) for variety. |
| 🎯 **Grader** | Evaluates answers against the question and its key facts. Uses a lower temperature (`0.1`) and a `max_tokens=100` ceiling. |
| 🗂️ **Record Answer Tool** | Updates the student's statistics and weak-topic records. |
| 💾 **Student Profile** | Stores progress in a local JSON file for future sessions. |

**Why use specialist agents?**

Separating question generation from grading makes the workflow easier to organize and maintain. The question writer focuses on creating useful questions, while the grader focuses on consistent evaluation.

---

## 🔄 How It Works

1. 🚀 **Start a session:** The application loads the existing student profile, if available.
2. 📚 **Choose a topic:** Select a topic manually or let the tutor prioritize weaker areas.
3. 🧠 **Generate a question:** The tutor consults the relevant learning material and delegates question generation.
4. ✍️ **Submit an answer:** Enter your response in the terminal.
5. 🎯 **Evaluate the answer:** The grader returns a `CORRECT` or `INCORRECT` verdict with a short explanation.
6. 📈 **Update progress:** The application records the result and updates the student's performance data.
7. 💾 **Save and continue:** Progress is persisted so future sessions can build on previous attempts.

---

## 📚 Available Study Topics

Study Buddy currently covers 14 technical topics related to the OpenAI Agents SDK.

| # | Topic | Topic ID |
|---:|---|---|
| 1 | 🧠 Agent Foundations | `agent-foundations` |
| 2 | ⚙️ Setup and Installation | `setup-and-installation` |
| 3 | ▶️ Running Agents and RunResult | `running-agents` |
| 4 | 🎭 Instructions and Personas | `instructions-and-personas` |
| 5 | 🔧 Function Tools | `function-tools` |
| 6 | 📦 Structured Outputs | `structured-outputs` |
| 7 | 🔀 Handoffs | `handoffs` |
| 8 | 🛡️ Guardrails | `guardrails` |
| 9 | 💬 Sessions and Conversation Memory | `sessions-and-memory` |
| 10 | 🌊 Streaming | `streaming` |
| 11 | 🔍 Tracing and Observability | `tracing` |
| 12 | 🧩 Models and Providers | `models-and-providers` |
| 13 | 🤝 Multi-Agent Orchestration | `multi-agent-orchestration` |
| 14 | 🚀 MCP and Deployment | `mcp-and-deployment` |

---

## 🛠️ Tech Stack

- 🐍 **Python** — Core application and tool logic.
- 🤖 **OpenAI Agents SDK** — Agent orchestration and specialist-agent-as-tool workflows.
- ✨ **Google Gemini 2.5 Flash** — Language model provider.
- 🔐 **python-dotenv** — Environment variable configuration.
- 💾 **JSON** — Local student-profile persistence.
- 🧪 **CLI** — Interactive terminal-based learning experience.
- 🔎 **OpenAI Tracing** — Optional tracing integration, depending on the configured environment and SDK setup.

---

## 🚀 Getting Started

Follow these steps to run Study Buddy locally.

### 1. ✅ Prerequisites

Make sure you have:

- Python 3.10 or later.
- Git, if you are cloning the repository.
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/).
- `uv` (recommended) or Python's built-in `venv` and `pip`.
- An OpenAI API key only if you want to configure the optional OpenAI tracing integration.

### 2. 📥 Clone or Open the Project

If the repository is hosted on GitHub, clone it and enter the project directory:

```bash
git clone <your-repository-url>
cd study-buddy
```

Alternatively, open your existing project folder in your terminal or VS Code.

### 3. 📦 Install Dependencies

**Option A — Using `uv` (recommended)**

```bash
uv sync
```

This installs the dependencies declared in the project's `pyproject.toml` and lockfile, when available.

**Option B — Using standard Python tools**

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

On Windows Command Prompt:

```bat
.venv\Scripts\activate.bat
```

On Linux or macOS:

```bash
source .venv/bin/activate
```

Install the required packages:

```bash
pip install openai-agents python-dotenv
```

### 4. 🔑 Configure Environment Variables

Create a file named `.env` in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: only if OpenAI tracing is configured
OPENAI_API_KEY=your_openai_api_key_here
```

Replace the placeholder values with your actual API keys.

🔒 **Security reminder:** Never commit your `.env` file or expose your API keys in public repositories.

Add the following entries to `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
*.py[cod]
```

If the student profile contains personal information, consider ignoring it as well:

```gitignore
student_profile.json
```

### 5. ▶️ Run Study Buddy

Using `uv`:

```bash
uv run python main.py
```

Or, with your virtual environment activated:

```bash
python main.py
```

🎉 You should now be able to start a study session from your terminal.

---

## 💻 Example Study Session

Here's an example of how a student interacts with Study Buddy.

```text
====================================================================
🤖 Welcome to the OpenAI Agents SDK Study Buddy!
====================================================================

👋 Loaded existing profile for Ada (Level: beginner).
📚 History: 1 topic(s) quizzed previously.

----------------------------------------
📋 MAIN MENU
----------------------------------------
1. Pick a topic to drill
2. Let tutor pick (prioritizes weak topics)
3. View session summary
q. Quit session
----------------------------------------

Select an option [1/2/3/q]: 1

📚 Available Topics:
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

⏳ Tutor is generating a question on 'function-tools'...

====================================================================
📝 TUTOR'S QUESTION
====================================================================

How does the `@function_tool` decorator determine the tool name,
description, and JSON schema for the model to use?

====================================================================

✍️ Enter your answer below (or type 'skip' to skip):

> It derives the tool name, description, and schema directly from the
  Python function's signature, docstring, and type hints.

⏳ Evaluating your answer and updating your profile...

====================================================================
🎯 VERDICT & FEEDBACK
====================================================================

✅ CORRECT

The student correctly identified that the function signature,
docstring, and type hints are used to derive the tool's schema and details.

====================================================================

----------------------------------------
📋 MAIN MENU
----------------------------------------

1. Pick a topic to drill
2. Let tutor pick (prioritizes weak topics)
3. View session summary
q. Quit session

Select an option [1/2/3/q]: q

====================================================================
🎓 SESSION SUMMARY FOR ADA (BEGINNER)
====================================================================

Topic ID                       Accuracy     Score      Status
--------------------------------------------------------------------
agent-foundations              100.0%       1/1        Mastered (>70%)
function-tools                 100.0%       1/1        Mastered (>70%)
--------------------------------------------------------------------

📊 Total Questions Answered: 2
🎯 Overall Accuracy:        100.0% (2/2)
💪 Weak topics:             None recorded! Keep up the good work!

💾 [Saved] Profile persisted to: student_profile.json

====================================================================
🎉 Thanks for studying! Goodbye!
```

*Note: This transcript illustrates the intended interaction; actual questions, evaluation results, and latency may vary.*

---

## 📊 Student Progress Tracking

Study Buddy records student performance to support more personalized practice.

Example session summary:

| Metric | Example |
|---|---|
| 👨‍🎓 Student | Ada |
| 📚 Questions answered | 2 |
| 🎯 Overall accuracy | 100% |
| 🧠 Topics practiced | 2 |
| 💪 Weak topics | None recorded |
| 💾 Persistence | `student_profile.json` |

The tutor can use recorded performance to prioritize topics that need more practice.

---

## ⚠️ Known Limitations & Areas for Improvement

No AI application is perfect. During profiling and testing, several limitations became apparent.

### 1. 🐢 Multi-Agent Latency Overhead

A single question-and-answer cycle can require several sequential model calls.

A representative workflow may include:

1. Tutor decides to retrieve notes.
2. Tutor decides to call the question writer.
3. Question writer generates a question.
4. Tutor prepares the question for the student.
5. Tutor initiates grading and answer recording.
6. Grader evaluates the answer.
7. Tutor presents the feedback.

Depending on tool execution and orchestration, this can involve up to seven model calls and create a noticeable delay. In testing, the feedback delay was approximately 4–7 seconds.

**Potential improvements:**

- ⚡ Reduce unnecessary tutor turns.
- 🛑 Use `tool_use_behavior="stop_on_first_tool"` where appropriate and supported by the chosen tool workflow.
- 🔧 Consider custom tool-output handling when the generated question can be returned directly.
- 📉 Measure latency before and after each optimization.

### 2. 🔁 Redundant Tutor Response

The question writer may already produce a complete question, but the tutor makes another model call to relay it to the student.

This extra step can increase latency and token usage without adding much value.

**Potential improvements:**

- Return the question writer's result directly when the workflow allows it.
- Use a suitable tool-stop strategy or custom output extractor.
- Preserve the tutor's role when additional context, validation, or personalization is genuinely needed.

### 3. 🎯 Rigid Key-Fact Grading

The grader compares answers against a limited set of key facts in `topics.json`.

A technically correct answer may receive an `INCORRECT` verdict if it uses different wording or explains a valid detail not covered by those facts.

**Potential improvements:**

- Add multiple acceptable answer patterns and equivalent technical explanations.
- Ask the grader to distinguish incorrect answers from partially correct answers.
- Include relevant context from authoritative course notes.
- Use structured grading outputs with a verdict, explanation, and confidence level.
- Test grading against a collection of correct, partially correct, and incorrect answers.

### 4. 💾 Basic JSON Persistence

Student progress is stored in a flat `student_profile.json` file.

This is simple and convenient for a prototype, but it has limitations:

- No file locking for simultaneous writes.
- No built-in schema migration strategy.
- Invalid JSON can prevent profile loading.
- Recovery logic may risk overwriting existing progress if errors are not handled carefully.

**Potential improvements:**

- Validate profile data before loading or saving.
- Create backups before overwriting existing progress.
- Write updates atomically.
- Add a profile schema version.
- Consider SQLite for more reliable persistence as the application grows.

### 5. 🧠 Growing Conversation Context

Passing the full conversation history through `result.to_input_list()` can cause the context to grow during longer sessions.

This may increase token consumption and latency and eventually approach the model's context-window limit.

**Potential improvements:**

- Summarize older conversation turns.
- Retain only the relevant learning context.
- Keep student statistics in the profile rather than repeatedly including the entire history.
- Use a bounded conversation window or session-specific memory strategy.
- Measure the impact of context trimming on grading quality.

---

## 🗺️ Future Roadmap

These are potential improvements for future versions of Study Buddy.

- [ ] ⚡ Reduce unnecessary model calls and response latency.
- [ ] 🎯 Improve grading accuracy and partial-credit handling.
- [ ] 🧠 Add adaptive difficulty levels.
- [ ] 📈 Track topic-level progress over time.
- [ ] 💾 Add safer persistence and profile backups.
- [ ] 🔄 Implement conversation summarization and context management.
- [ ] 🧪 Add automated tests for tools, grading, and profile updates.
- [ ] 🌐 Explore a web-based interface for easier access.
- [ ] 📊 Add a student dashboard with progress visualizations.
- [ ] 🔐 Improve API-key handling, validation, and error reporting.

---

## 🔐 Security & Best Practices

- Never hardcode API keys in source files.
- Keep `.env` and sensitive student data out of public repositories.
- Handle API errors and rate limits gracefully.
- Validate profile data before loading it.
- Avoid logging sensitive student information.
- Review tool inputs and outputs when adding new capabilities.
- Add tests before introducing more complex agent workflows.

---

## 🎯 Project Goal

The goal of Study Buddy is to demonstrate how multiple specialized AI agents can work together to create a personalized technical learning experience.

It combines **agent orchestration, tool calling, automated evaluation, and persistent student progress** in a practical Python application.

The project also explores an important engineering lesson: adding more agents does not automatically make a system better. Good orchestration, efficient model calls, reliable data handling, and thoughtful evaluation are equally important.

---

## 🤝 Contributing

Ideas, bug reports, and improvements are welcome!

If you'd like to contribute:

1. 🍴 Fork the repository.
2. 🌿 Create a feature branch.
3. 💻 Make your changes.
4. 🧪 Test the updated workflow.
5. 📬 Submit a pull request with a clear description.

Please keep changes focused, document important behavior, and avoid committing secrets or personal student data.

---

## 📄 License

Add your chosen open-source license before publishing the project. For example, you can use an MIT License if that matches your intended distribution and usage.

---

<div align="center">

### 🌟 Learn. Practice. Improve. Repeat. 🚀

**Study Buddy — Your personal AI-powered technical learning companion.**

Built with 🐍 Python, 🤖 AI agents, and a passion for learning.

</div>
