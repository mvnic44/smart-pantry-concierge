# ruff: noqa
import datetime
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.tools import load_memory, preload_memory
from google.adk.agents.run_config import RunConfig, StreamingMode

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from app.a2ui_utils import a2ui_callback

from app.tools import (
    search_recipes,
    save_favorite_recipe,
    get_favorite_recipes,
    scale_recipe_servings,
    generate_recipe_image,
    save_user_preference,
    load_user_preferences,
)

# Enforce non-streaming mode for adk web playground so A2UI cards render properly
try:
    from google.adk.cli import api_server
    if hasattr(api_server, "RunAgentRequest"):
        _OriginalRunAgentRequest = api_server.RunAgentRequest
        class NonStreamingRunAgentRequest(_OriginalRunAgentRequest):
            def __init__(self, **data):
                data["streaming"] = False
                super().__init__(**data)
        api_server.RunAgentRequest = NonStreamingRunAgentRequest
except Exception as e:
    print(f"Warning: Could not patch api_server.RunAgentRequest: {e}", flush=True)

memory_service = VertexAiMemoryBankService(
    project="qwiklabs-gcp-02-47994b847bd6",
    location="us-east1",
    agent_engine_id="1872153841776984064",
)

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the Smart Pantry Recipe Concierge, an AI culinary assistant with long-term memory. "
        "Your goal is to help home cooks discover recipes based on ingredients they have on hand, "
        "filter recipes by dietary preferences, save favorite recipes to their personal cookbook, "
        "scale recipe portion sizes for different group numbers, generate dish imagery, and remember user dietary restrictions. "
        "Whenever a user shares dietary preferences, allergies, or ingredient dislikes (e.g., 'I am allergic to peanuts' or 'I follow a vegan diet'), "
        "use your save_user_preference tool to record it in long-term memory. "
        "Use load_user_preferences, load_memory, or preload_memory to recall stored allergies and preferences across sessions when suggesting recipes or answering food questions. "
        "Use search_recipes when asked for recipe ideas or what to cook with specific ingredients. "
        "Use save_favorite_recipe when the user wants to save or bookmark a recipe. "
        "Use get_favorite_recipes when the user asks to see their saved or favorite recipes. "
        "Use scale_recipe_servings when the user wants to adjust portion sizes for a specific number of people. "
        "Use generate_recipe_image when the user wants to see a visual representation of a dish."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        load_memory,
        preload_memory,
        load_user_preferences,
        save_user_preference,
        search_recipes,
        save_favorite_recipe,
        get_favorite_recipes,
        scale_recipe_servings,
        generate_recipe_image,
    ],
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
