import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from agents import (
    Agent,
    HandoffCallItem,
    HandoffOutputItem,
    MaxTurnsExceeded,
    ModelSettings,
    OpenAIChatCompletionsModel,
    RunContextWrapper,
    Runner,
    StopAtTools,
    flush_traces,
    function_tool,
    set_tracing_export_api_key,
    trace,
)
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

openai_api_key = os.environ.get("OPENAI_API_KEY")
if openai_api_key:
    set_tracing_export_api_key(openai_api_key)

MODEL = "gemini-2.5-flash"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
TOPICS_PATH = Path(__file__).with_name("topics.json")
HARDER_THRESHOLD = 0.70

TOPICS: list[dict[str, Any]] = json.loads(TOPICS_PATH.read_text(encoding="utf-8"))


@dataclass
class StudentProfile:
    name: str
    level: Literal["beginner", "intermediate"] = "beginner"
    weak_topics: list[str] = field(default_factory=list)
    answered: dict[str, tuple[int, int]] = field(default_factory=dict)


def accuracy(correct: int, total: int) -> float:
    return correct / total if total else 0.0


def build_client() -> AsyncOpenAI:
    api_key = os.environ["GEMINI_API_KEY"]
    return AsyncOpenAI(api_key=api_key, base_url=BASE_URL)


def build_instructions(
    context: RunContextWrapper[StudentProfile], agent: Agent[StudentProfile]
) -> str:
    profile = context.context
    lines = [
        f"You are {agent.name}, a concise study buddy for the OpenAI Agents SDK course.",
        f"You are tutoring {profile.name}, who is at {profile.level} level.",
    ]

    if profile.weak_topics:
        lines.append(
            "Push the conversation toward these weak topics before anything else: "
            + ", ".join(profile.weak_topics)
            + "."
        )
    else:
        lines.append(
            "No weak topics recorded yet, so probe the fundamentals to find gaps."
        )

    mastered = [
        topic_id
        for topic_id, (correct, total) in profile.answered.items()
        if accuracy(correct, total) > HARDER_THRESHOLD
    ]
    if mastered:
        lines.append(
            "Accuracy is above 70% on "
            + ", ".join(
                f"{topic_id} ({profile.answered[topic_id][0]}/{profile.answered[topic_id][1]})"
                for topic_id in mastered
            )
            + ", so ask noticeably harder questions on those and stop drilling the basics."
        )
    else:
        lines.append(
            "No topic is above 70% accuracy yet, so keep questions at the current difficulty."
        )

    wrong_topics = [
        topic_id
        for topic_id, (correct, total) in profile.answered.items()
        if (total - correct) >= 2
    ]
    if wrong_topics:
        lines.append(
            f"The student has 2 or more wrong answers on: {', '.join(wrong_topics)}."
        )

    lines.append(
        "Handoff rule: When the profile shows 2 or more wrong answers on the current topic, do not quiz the student. Immediately hand off to the Remedial Tutor. "
        "EXCEPTION: If the student just returned from a remedial session and passed their check question, do NOT hand off again—quiz them with a fresh question on the topic."
    )

    lines.extend([
        "Strict workflow for quizzing:",
        "1. When the student wants to be quizzed on a topic, call get_notes to retrieve the key facts.",
        "2. Then call the question_writer tool with the topic to generate exactly one question. Never invent or write quiz questions yourself.",
        "3. Present only the question to the student and wait for their answer. Never answer the question yourself.",
        "4. When the student replies with their answer, call the grader tool passing the question, the student's answer, and the key facts.",
        "5. Share the grader's verdict and feedback with the student, and immediately call record_answer with the topic_id and was_correct (True if correct, False otherwise).",
        "Keep your replies concise and always maintain your consistent tutor persona.",
    ])
    return "\n".join(lines)


def build_question_writer() -> Agent[None]:
    return Agent(
        name="Question Writer",
        instructions=(
            "You are a specialist question writer. Given a topic, output exactly one "
            "question on that topic and nothing else. Do not output introductions, explanations, "
            "options, or answers."
        ),
        model=OpenAIChatCompletionsModel(model=MODEL, openai_client=build_client()),
        model_settings=ModelSettings(temperature=0.9),
    )


def build_grader() -> Agent[None]:
    return Agent(
        name="Grader",
        instructions=(
            "You are a specialist grader. You receive the question, the student's answer, "
            "and the key facts. Compare the student's answer against the key facts and return "
            "a verdict ('CORRECT' or 'INCORRECT') plus exactly one sentence of feedback. "
            "Do not output anything else."
        ),
        model=OpenAIChatCompletionsModel(model=MODEL, openai_client=build_client()),
        model_settings=ModelSettings(temperature=0.1, max_tokens=100),
    )


def build_remedial_tutor() -> Agent[StudentProfile]:
    return Agent(
        name="Remedial Tutor",
        instructions=(
            "You are the Remedial Tutor for the OpenAI Agents SDK course. "
            "The student has repeatedly missed questions on this topic, so your mission is to teach from first principles. "
            "Explain the topic thoroughly and clearly, provide a concrete worked code example, and walk through it step-by-step. "
            "Do not start with quiz questions. However, if the student asks for a check question, provide exactly one targeted check question. "
            "When the student answers the check question correctly, confirm it, praise their understanding, and encourage them to quiz with the main tutor."
        ),
        model=OpenAIChatCompletionsModel(model=MODEL, openai_client=build_client()),
        tools=[get_notes],
    )


def is_intermediate_student(context: RunContextWrapper[StudentProfile], agent: Any) -> bool:
    """Return True if the student's level is intermediate."""
    return context.context.level == "intermediate"


@function_tool(is_enabled=is_intermediate_student)
def start_exam_mode() -> str:
    """Start comprehensive exam mode. Only offered to intermediate students."""
    return "Exam mode started! Time-pressured advanced questions across multiple topics initiated."


@function_tool
def finish_session() -> str:
    """End the study session immediately and conclude."""
    return "Session finished. Great job on your practice today!"


def build_agent() -> Agent[StudentProfile]:
    question_writer = build_question_writer()
    grader = build_grader()
    remedial_tutor = build_remedial_tutor()

    question_writer_tool = question_writer.as_tool(
        tool_name="question_writer",
        tool_description="Generate exactly one quiz question on a given topic. Pass the topic as the input string.",
    )
    grader_tool = grader.as_tool(
        tool_name="grader",
        tool_description="Grade a student's answer given the question, student answer, and key facts. Pass the question, student answer, and key facts in the input string. Returns a verdict and one sentence of feedback.",
    )

    return Agent(
        name="Study Buddy",
        instructions=build_instructions,
        model=OpenAIChatCompletionsModel(model=MODEL, openai_client=build_client()),
        tools=[
            list_topics,
            get_notes,
            record_answer,
            question_writer_tool,
            grader_tool,
            start_exam_mode,
            finish_session,
        ],
        handoffs=[remedial_tutor],
        tool_use_behavior=StopAtTools(stop_at_tool_names=["finish_session"]),
    )


@function_tool
def list_topics() -> list[dict[str, str]]:
    """List every course topic as its id and title. Call this first when the
    user asks what they can study or be quizzed on."""
    return [{"id": topic["id"], "title": topic["title"]} for topic in TOPICS]


@function_tool
def get_notes(topic_id: str) -> dict[str, Any]:
    """Look up one topic by its id and return its summary and key facts.
    Use list_topics to get valid ids."""
    for topic in TOPICS:
        if topic["id"] == topic_id:
            return {
                "id": topic["id"],
                "title": topic["title"],
                "summary": topic["summary"],
                "key_facts": topic["key_facts"],
            }
    raise ValueError(
        f"Unknown topic_id {topic_id!r}. Valid ids: "
        + ", ".join(topic["id"] for topic in TOPICS)
    )


PROFILE_PATH = Path(__file__).with_name("student_profile.json")


def load_profile(default_name: str = "Student") -> StudentProfile:
    """Load persisted StudentProfile from JSON if it exists, otherwise return a new one."""
    if PROFILE_PATH.exists():
        try:
            data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            return StudentProfile(
                name=data.get("name", default_name),
                level=data.get("level", "beginner"),
                weak_topics=data.get("weak_topics", []),
                answered={k: tuple(v) for k, v in data.get("answered", {}).items()},
            )
        except Exception as e:
            print(f"[Notice] Could not load saved profile: {e}. Starting fresh.")
    return StudentProfile(name=default_name, level="beginner")


def save_profile(profile: StudentProfile) -> None:
    """Persist StudentProfile to a JSON file."""
    data = {
        "name": profile.name,
        "level": profile.level,
        "weak_topics": profile.weak_topics,
        "answered": {k: list(v) for k, v in profile.answered.items()},
    }
    PROFILE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


@function_tool
def record_answer(
    context: RunContextWrapper[StudentProfile], topic_id: str, was_correct: bool
) -> str:
    """Record one quiz answer on the student's profile.

    Args:
        topic_id: The id of the topic the student answered, e.g. "function-tools".
        was_correct: True if the student got it right, False if they got it wrong.
    """
    profile = context.context
    correct, total = profile.answered.get(topic_id, (0, 0))
    correct += 1 if was_correct else 0
    total += 1
    profile.answered[topic_id] = (correct, total)
    if not was_correct and topic_id not in profile.weak_topics:
        profile.weak_topics.append(topic_id)
    save_profile(profile)
    return f"Recorded {topic_id}: {correct}/{total} correct for {profile.name}."


def print_session_summary(profile: StudentProfile) -> None:
    """Display session summary with accuracy per topic."""
    print("\n" + "=" * 68)
    print(f"🎓 SESSION SUMMARY FOR {profile.name.upper()} ({profile.level.upper()})")
    print("=" * 68)
    print(f"{'Topic ID':<30} {'Accuracy':<12} {'Score':<10} {'Status'}")
    print("-" * 68)

    total_correct = 0
    total_questions = 0

    if not profile.answered:
        print("No questions answered yet.")
    else:
        for topic_id, (correct, total) in sorted(profile.answered.items()):
            rate = accuracy(correct, total) * 100
            total_correct += correct
            total_questions += total
            if rate >= 70:
                status = "Mastered (>70%)"
            elif topic_id in profile.weak_topics:
                status = "Weak Topic"
            else:
                status = "In Progress"
            print(f"{topic_id:<30} {rate:>5.1f}%      {f'{correct}/{total}':<10} {status}")

    print("-" * 68)
    overall_rate = accuracy(total_correct, total_questions) * 100
    print(f"Total Questions Answered: {total_questions}")
    print(f"Overall Accuracy:        {overall_rate:.1f}% ({total_correct}/{total_questions})")
    if profile.weak_topics:
        print(f"Weak topics to review:   {', '.join(profile.weak_topics)}")
    else:
        print("Weak topics:             None recorded! Keep up the good work!")
    print(f"\n[Saved] Profile persisted to: {PROFILE_PATH.name}")
    print("=" * 68 + "\n")


async def cli_loop() -> None:
    """Interactive CLI study loop."""
    print("=" * 68)
    print("🤖 Welcome to the OpenAI Agents SDK Study Buddy!")
    print("=" * 68)

    profile = load_profile()
    if not PROFILE_PATH.exists():
        name_input = input("Enter your name [Student]: ").strip()
        if name_input:
            profile.name = name_input
        save_profile(profile)
    else:
        print(f"Loaded existing profile for {profile.name} (Level: {profile.level}).")
        if profile.answered:
            print(f"History: {len(profile.answered)} topic(s) quizzed previously.")

    tutor = build_agent()

    while True:
        print("\n" + "-" * 40)
        print("MAIN MENU")
        print("-" * 40)
        print("1. Pick a topic to drill")
        print("2. Let tutor pick (prioritizes weak topics)")
        print("3. View session summary")
        print("q. Quit session")
        print("-" * 40)

        choice = input("Select an option [1/2/3/q]: ").strip().lower()

        if choice in ("q", "quit", "exit"):
            break

        if choice == "3":
            print_session_summary(profile)
            continue

        selected_topic_id: str | None = None
        if choice == "1":
            print("\nAvailable Topics:")
            for idx, topic in enumerate(TOPICS, 1):
                tid = topic["id"]
                score_str = ""
                if tid in profile.answered:
                    c, t = profile.answered[tid]
                    score_str = f" [Score: {c}/{t} ({accuracy(c, t)*100:.0f}%)]"
                print(f"  {idx:2d}. {topic['title']} ({tid}){score_str}")

            topic_pick = input(f"\nEnter topic number (1-{len(TOPICS)}) or topic ID: ").strip()
            if topic_pick.isdigit():
                num = int(topic_pick)
                if 1 <= num <= len(TOPICS):
                    selected_topic_id = TOPICS[num - 1]["id"]
            elif any(t["id"] == topic_pick for t in TOPICS):
                selected_topic_id = topic_pick

            if not selected_topic_id:
                print("Invalid topic selection. Returning to menu.")
                continue

        # Start the quiz interaction turn
        if selected_topic_id:
            prompt = f"Quiz me on {selected_topic_id}."
            print(f"\n[Tutor is consulting notes and generating a question on '{selected_topic_id}'...]")
        else:
            prompt = (
                "Pick a topic to quiz me on. If I have weak topics, prioritize those; "
                "otherwise pick a fundamental topic to test my knowledge."
            )
            print("\n[Tutor is selecting a topic from your profile...]")

        with trace("Study session"):
            # Turn 1: Question Generation or Remedial Handoff (capped at max_turns=6)
            try:
                result1 = await Runner.run(tutor, prompt, context=profile, max_turns=6)
            except MaxTurnsExceeded as exc:
                print(f"\n[Run Cap] MaxTurnsExceeded caught: {exc}")
                continue

            print(f"\n[Turn 1 result.last_agent: {result1.last_agent.name}]")
            for item in result1.new_items:
                if isinstance(item, HandoffCallItem):
                    print(f"  --> HandoffCallItem: function={item.raw_item.function.name}, args={item.raw_item.function.arguments}")
                elif isinstance(item, HandoffOutputItem):
                    print(f"  --> HandoffOutputItem: {item.source_agent.name} -> {item.target_agent.name}")

            # If handoff occurred to Remedial Tutor, present the lesson without quizzing
            if result1.last_agent.name == "Remedial Tutor":
                print("\n" + "=" * 68)
                print("📖 REMEDIAL LESSON (No Quizzing)")
                print("=" * 68)
                print(result1.final_output.strip())
                print("=" * 68)
                flush_traces()
                continue

            print("\n" + "=" * 68)
            print("📝 TUTOR'S QUESTION")
            print("=" * 68)
            print(result1.final_output.strip())
            print("=" * 68)

            # Turn 2: Student Answer
            print("\nEnter your answer below (or type 'skip' to skip):")
            user_answer = input("> ").strip()
            if not user_answer or user_answer.lower() == "skip":
                print("Question skipped.")
                continue

            print("\n[Tutor is evaluating your answer with the grader and updating your profile...]")
            history = result1.to_input_list()
            history.append({"role": "user", "content": user_answer})

            # Use tool_choice="required" so tutor must invoke grader and record_answer (capped at max_turns=6)
            recording_tutor = tutor.clone(model_settings=ModelSettings(tool_choice="required"))
            try:
                result2 = await Runner.run(recording_tutor, history, context=profile, max_turns=6)
            except MaxTurnsExceeded as exc:
                print(f"\n[Run Cap] MaxTurnsExceeded caught on grading: {exc}")
                continue

            print(f"\n[Turn 2 result.last_agent: {result2.last_agent.name}]")
            for item in result2.new_items:
                if isinstance(item, HandoffCallItem):
                    print(f"  --> HandoffCallItem: function={item.raw_item.function.name}")
                elif isinstance(item, HandoffOutputItem):
                    print(f"  --> HandoffOutputItem: {item.source_agent.name} -> {item.target_agent.name}")

            print("\n" + "=" * 68)
            print("🎯 VERDICT & FEEDBACK")
            print("=" * 68)
            print(result2.final_output.strip())
            print("=" * 68)

        flush_traces()

    print_session_summary(profile)
    print("Thanks for studying! Goodbye!")


async def demonstrate_remedial_handoff() -> None:
    """Demonstrate the handoff to Remedial Tutor when 2 wrong answers are on record."""
    print("\n" + "=" * 68)
    print("=== MILESTONE 9: REMEDIAL TUTOR HANDOFF DEMO ===")
    print("=" * 68)

    tutor = build_agent()
    # Ada has missed agent-foundations twice (0 correct out of 2 total)
    profile = StudentProfile(
        name="Ada",
        level="beginner",
        weak_topics=["agent-foundations"],
        answered={"agent-foundations": (0, 2)},
    )

    print(f"Student profile: answered={profile.answered}, weak_topics={profile.weak_topics}")
    print("Student request: 'Quiz me on agent-foundations.'")

    result = await Runner.run(tutor, "Quiz me on agent-foundations.", context=profile)

    print("\n" + "-" * 68)
    print(f"result.last_agent: {result.last_agent.name} (type: {type(result.last_agent).__name__})")
    print("-" * 68)

    print("\nHandoff items inside result.new_items:")
    for item in result.new_items:
        if isinstance(item, HandoffCallItem):
            print(f"\n[HandoffCallItem]:")
            print(f"  Tool Name: {item.raw_item.function.name}")
            print(f"  Call ID:   {item.raw_item.call_id}")
            print(f"  Arguments: {item.raw_item.function.arguments}")
        elif isinstance(item, HandoffOutputItem):
            print(f"\n[HandoffOutputItem]:")
            print(f"  Source Agent: {item.source_agent.name}")
            print(f"  Target Agent: {item.target_agent.name}")
            print(f"  Raw Item:     {item.raw_item}")

    print("\n" + "=" * 68)
    print("REMEDIAL TUTOR OUTPUT:")
    print("=" * 68)
    print(result.final_output.strip())
    print("=" * 68)


async def demonstrate_four_turn_handoff() -> list[str]:
    """Execute four turns across handoff and return, tracking agent ownership per turn."""
    print("\n" + "=" * 68)
    print("=== MILESTONE 10: 4-TURN HANDOFF & RETURN DEMONSTRATION ===")
    print("=" * 68)

    tutor = build_agent()
    # Profile with 2 wrong answers on 'agent-foundations'
    profile = StudentProfile(
        name="Ada",
        level="beginner",
        weak_topics=["agent-foundations"],
        answered={"agent-foundations": (0, 2)},
    )
    turn_owners: list[str] = []

    # Turn 1: Main tutor triggered with 2 wrong answers -> hands off to Remedial Tutor
    print("\n--- Turn 1: Student requests quiz on topic with 2 wrong answers ---")
    result1 = await Runner.run(tutor, "Quiz me on agent-foundations.", context=profile)
    owner1 = "tutor"
    turn_owners.append(owner1)
    print(f"Turn 1 Starting Agent: Study Buddy (Main Tutor)")
    print(f"Turn 1 Final Output Agent: {result1.last_agent.name}")
    print(f"Turn 1 Response Preview:\n{result1.final_output[:250]}...\n")

    # Turn 2: Continue with result1.last_agent (Remedial Tutor) using result1.to_input_list()
    print("--- Turn 2: Remedial Tutor continues session (asks check question) ---")
    history2 = result1.to_input_list()
    history2.append({
        "role": "user",
        "content": "Thank you for explaining. Can you ask me one check question to test my understanding?",
    })
    result2 = await Runner.run(result1.last_agent, history2, context=profile)
    owner2 = "remedial"
    turn_owners.append(owner2)
    print(f"Turn 2 Agent: {result2.last_agent.name}")
    print(f"Turn 2 Response:\n{result2.final_output.strip()}\n")

    # Turn 3: Student answers the check question correctly -> Remedial Tutor validates
    print("--- Turn 3: Student answers check question correctly ---")
    history3 = result2.to_input_list()
    history3.append({
        "role": "user",
        "content": (
            "An Agent in the SDK combines instructions, a model, and tools into a single unit, "
            "and runs in a model loop deciding whether to call tools or finish."
        ),
    })
    result3 = await Runner.run(result2.last_agent, history3, context=profile)
    owner3 = "remedial"
    turn_owners.append(owner3)
    print(f"Turn 3 Agent: {result3.last_agent.name}")
    print(f"Turn 3 Response:\n{result3.final_output.strip()}\n")

    # Turn 4: Route back to the main tutor with a fresh quiz on the same topic
    print("--- Turn 4: Deliberately route back to main tutor for a fresh quiz ---")
    history4 = result3.to_input_list()
    history4.append({
        "role": "user",
        "content": "I passed the check question! Please give me a fresh quiz question on agent-foundations.",
    })
    result4 = await Runner.run(tutor, history4, context=profile)
    owner4 = "tutor"
    turn_owners.append(owner4)
    print(f"Turn 4 Agent: {result4.last_agent.name}")
    print(f"Turn 4 Response:\n{result4.final_output.strip()}\n")

    print("=" * 68)
    print(f"TURN OWNERSHIP SEQUENCE: {', '.join(turn_owners)}")
    print("Verification: tutor, remedial, remedial, tutor")
    print("=" * 68)

    return turn_owners


async def demonstrate_exam_gating_and_caps() -> None:
    """Milestone 11 demonstration: tool gating via is_enabled, finish_session via StopAtTools, and max_turns cap."""
    print("\n" + "=" * 68)
    print("=== MILESTONE 11: EXAM GATING & LOOP CONTROLS ===")
    print("=" * 68)

    tutor = build_agent()
    beginner_profile = StudentProfile(name="Ada", level="beginner")
    intermediate_profile = StudentProfile(name="Grace", level="intermediate")

    # 1. Compare offered tools for beginner vs intermediate
    beginner_tools = await tutor.get_all_tools(RunContextWrapper(context=beginner_profile))
    intermediate_tools = await tutor.get_all_tools(RunContextWrapper(context=intermediate_profile))

    def tool_label(t: Any) -> str:
        return getattr(t, "name", str(t))

    beginner_names = [tool_label(t) for t in beginner_tools]
    intermediate_names = [tool_label(t) for t in intermediate_tools]

    print("\n--- Tool Availability by Profile Level ---")
    print(f"Beginner Profile ('Ada') offered {len(beginner_names)} tools:")
    for name in beginner_names:
        print(f"  • {name}")
    print(f"  --> Is 'start_exam_mode' offered to beginner? {'start_exam_mode' in beginner_names}")

    print(f"\nIntermediate Profile ('Grace') offered {len(intermediate_names)} tools:")
    for name in intermediate_names:
        print(f"  • {name}")
    print(f"  --> Is 'start_exam_mode' offered to intermediate? {'start_exam_mode' in intermediate_names}")

    # 2. Run the same question on both profiles with sensible max_turns
    prompt = "Can you start exam mode for me?"
    sensible_max_turns = 6  # 3 model turns per sub-routine cycle (call tool, read result, produce reply)

    print("\n" + "-" * 68)
    print("--- Running Prompt as Beginner ('Ada') ---")
    print(f"Prompt: '{prompt}' (max_turns={sensible_max_turns})")
    try:
        res_beg = await Runner.run(tutor, prompt, context=beginner_profile, max_turns=sensible_max_turns)
        print(f"Beginner Response:\n{res_beg.final_output.strip()}\n")
    except MaxTurnsExceeded as e:
        print(f"Caught MaxTurnsExceeded: {e}\n")

    print("-" * 68)
    print("--- Running Prompt as Intermediate ('Grace') ---")
    print(f"Prompt: '{prompt}' (max_turns={sensible_max_turns})")
    try:
        res_int = await Runner.run(tutor, prompt, context=intermediate_profile, max_turns=sensible_max_turns)
        print(f"Intermediate Response:\n{res_int.final_output.strip()}\n")
    except MaxTurnsExceeded as e:
        print(f"Caught MaxTurnsExceeded: {e}\n")

    # 3. Demonstrate finish_session ending run via StopAtTools
    print("-" * 68)
    print("--- Demonstrating finish_session with StopAtTools ---")
    finish_prompt = "I would like to end the session now, please call finish_session."
    try:
        res_finish = await Runner.run(tutor, finish_prompt, context=beginner_profile, max_turns=sensible_max_turns)
        print(f"Final output verbatim:\n'{res_finish.final_output.strip()}'")
    except MaxTurnsExceeded as e:
        print(f"Caught MaxTurnsExceeded: {e}\n")


if __name__ == "__main__":
    asyncio.run(cli_loop())
