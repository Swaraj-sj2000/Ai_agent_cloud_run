import os
import logging
import google.cloud.logging
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.agents import SequentialAgent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.langchain_tool import LangchainTool

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

# ---------------------------------------------------------------------------
# Logging & environment
# ---------------------------------------------------------------------------
try:
    cloud_logging_client = google.cloud.logging.Client()
    cloud_logging_client.setup_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

load_dotenv()
model_name = os.getenv("MODEL", "gemini-2.5-flash")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def save_topic_to_state(tool_context: ToolContext, topic: str) -> dict:
    """
    Saves the user's topic/query to shared agent state so downstream
    agents can access it.
    """
    tool_context.state["TOPIC"] = topic
    logging.info(f"[State] Topic saved: {topic}")
    return {"status": "success", "topic": topic}


# Wikipedia tool — free, no API key, safe for trial accounts
wikipedia_tool = LangchainTool(
    tool=WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(top_k_results=2))
)


# ---------------------------------------------------------------------------
# Agent 1 — Researcher
# Uses Wikipedia to fetch real, current content about the topic
# ---------------------------------------------------------------------------
researcher_agent = Agent(
    name="researcher",
    model=model_name,
    description="Searches Wikipedia to gather factual information about the user's topic.",
    instruction="""
    You are a research assistant. The user wants to learn about: { TOPIC }

    Use the Wikipedia search tool to find relevant, factual information about this topic.
    Retrieve enough content to support a good summary AND a topic classification.

    Return ALL the raw information you find — do not filter or summarize yet.
    Just gather the facts.
    """,
    tools=[wikipedia_tool],
    output_key="raw_research",
)


# ---------------------------------------------------------------------------
# Agent 2 — Summarizer
# Condenses the raw research into a clean, readable summary
# ---------------------------------------------------------------------------
summarizer_agent = Agent(
    name="summarizer",
    model=model_name,
    description="Summarizes raw research into a concise, readable overview.",
    instruction="""
    You are an expert summarizer. Below is RAW_RESEARCH gathered about a topic.

    Write a clear, concise summary following these rules:
    - Start with a 2-3 sentence overview (TL;DR)
    - Follow with 4-6 bullet points covering the most important facts
    - Keep the total length under 200 words
    - Use plain, accessible language — no jargon

    RAW_RESEARCH:
    { raw_research }
    """,
    output_key="summary",
)


# ---------------------------------------------------------------------------
# Agent 3 — Classifier
# Categorises the topic based on the research content
# ---------------------------------------------------------------------------
classifier_agent = Agent(
    name="classifier",
    model=model_name,
    description="Classifies the topic into one or more categories and explains why.",
    instruction="""
    You are a content classification expert.

    Based on the RAW_RESEARCH below, classify the topic into the most relevant
    categories from this list:
      Science & Technology | Politics & Governance | Business & Economy |
      Health & Medicine | Environment & Climate | Sports | Arts & Culture |
      History | Education | Society & Human Interest

    Rules:
    - You may assign 1 to 3 categories (pick only what clearly fits)
    - For each category you assign, give a one-sentence justification
    - If nothing fits well, use "General Knowledge" with a brief reason

    RAW_RESEARCH:
    { raw_research }
    """,
    output_key="classification",
)


# ---------------------------------------------------------------------------
# Agent 4 — Final Presenter
# Assembles summary + classification into one polished response
# ---------------------------------------------------------------------------
presenter_agent = Agent(
    name="presenter",
    model=model_name,
    description="Combines the summary and classification into a single, well-formatted final answer.",
    instruction="""
    You are a friendly analyst presenting a research brief to the user.

    Combine the SUMMARY and CLASSIFICATION below into one polished response
    using this exact format:

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    🔍 Topic: { TOPIC }
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    📋 SUMMARY
    [Insert the SUMMARY here]

    🏷️ CLASSIFICATION
    [Insert the CLASSIFICATION here, formatted as a clean list]

    📎 Source: Wikipedia
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Keep it clean and professional. Do not add extra commentary beyond what
    the SUMMARY and CLASSIFICATION already contain.

    SUMMARY:
    { summary }

    CLASSIFICATION:
    { classification }
    """,
)


# ---------------------------------------------------------------------------
# Sequential workflow: Research → Summarize → Classify → Present
# ---------------------------------------------------------------------------
analysis_workflow = SequentialAgent(
    name="analysis_workflow",
    description="Full pipeline: fetch info, summarize it, classify it, present it.",
    sub_agents=[
        researcher_agent,   # Step 1: fetch Wikipedia content
        summarizer_agent,   # Step 2: produce clean summary
        classifier_agent,   # Step 3: classify the topic
        presenter_agent,    # Step 4: assemble final formatted output
    ],
)


# ---------------------------------------------------------------------------
# Root agent — entry point for all conversations
# ---------------------------------------------------------------------------
root_agent = Agent(
    name="news_analyst",
    model=model_name,
    description=(
        "A smart research analyst that takes any topic, fetches the latest "
        "information from Wikipedia, summarizes it clearly, and classifies "
        "it into relevant categories."
    ),
    instruction="""
    You are a smart research analyst assistant.

    When the conversation starts:
    - Greet the user warmly and briefly
    - Tell them they can ask about ANY topic — a news event, a concept,
      a person, a country, a technology, anything
    - Ask them: "What topic would you like me to research and analyse?"

    When the user provides a topic:
    - Use the 'save_topic_to_state' tool to save their topic
    - Then immediately hand off to the 'analysis_workflow' agent
    - Do NOT try to answer the question yourself

    Keep your greeting to 2-3 sentences maximum.
    """,
    tools=[save_topic_to_state],
    sub_agents=[analysis_workflow],
)
