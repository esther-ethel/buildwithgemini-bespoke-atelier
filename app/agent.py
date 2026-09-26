# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from app.a2ui_utils import a2ui_callback
from app.tools import (
    get_patterns_by_aesthetic,
    get_pattern_by_id,
    save_user_profile,
    get_user_profile,
    save_drafted_project,
    list_user_projects,
    calculate_pattern_requirements,
    generate_pattern_svg,
    get_climate_fabric_advice,
    search_historic_fashion,
    generate_fashion_flat_sketch,
    generate_garment_motion_preview,
)

# Load sandbox code executor configuration from deployment_metadata.json
metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
sandbox_executor = None

if metadata_path.exists():
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            dep_meta = json.load(f)
        sandbox_id = dep_meta.get("sandbox_resource_name")
        engine_id = dep_meta.get("remote_agent_runtime_id")
        if sandbox_id or engine_id:
            sandbox_executor = AgentEngineSandboxCodeExecutor(
                sandbox_resource_name=sandbox_id,
                agent_engine_resource_name=engine_id if not sandbox_id else None
            )
    except Exception:
        sandbox_executor = None

# Configure Memory Bank service for future redeployments (reuse Agent Engine 3367485257505832960)
MEMORY_BANK_ID = "3367485257505832960"
PROJECT_ID = "qwiklabs-gcp-03-7d5352e0a1dc"
LOCATION = "us-east1"

memory_service = VertexAiMemoryBankService(
    project=PROJECT_ID,
    location=LOCATION,
    agent_engine_id=MEMORY_BANK_ID,
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback triggered after each turn to extract and persist durable facts to Memory Bank."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        pass
    return None


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city or query to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# Build A2UI System Instruction (version 0.8 with Basic Catalog)
a2ui_schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = a2ui_schema_manager.generate_system_prompt(
    role_description=(
        "You are the Bespoke Atelier & Pattern Concierge agent. You help sewists and tailors save body measurement "
        "profiles, explore sewing pattern templates across aesthetic styles (Old Money, Vintage 1950s, Cottagecore, Minimalist), "
        "calculate parametric pattern drafting ease and fabric yardage requirements, generate 2D vector SVG pattern files, "
        "render 2D technical fashion flat sketches, fetch live climate fabric weight advice via Open-Meteo, "
        "search costume archives at The Met Museum, and draft bespoke sewing projects.\n\n"
        "TOOL SELECTION MANDATES:\n"
        "1. When the user asks for a technical flat sketch, garment drawing, visual design, or fashion image preview, ALWAYS call `generate_fashion_flat_sketch(garment_description=..., aesthetic=...)` to generate a 2D technical fashion flat image.\n"
        "2. When the user asks to draft a pattern piece, vector layout, or SVG pattern, ALWAYS call `generate_pattern_svg(pattern_name=..., aesthetic=...)`.\n"
        "3. When the user asks for fabric requirements, ease math, or cut lists, call `calculate_pattern_requirements`.\n"
        "4. When the user asks for museum garments or historical fashion, call `search_historic_fashion`.\n"
        "5. When the user asks for weather or climate fabric recommendations, call `get_climate_fabric_advice`.\n"
        "6. When the user asks for a 360-degree turntable video, motion preview, textile drape video, or mannequin video preview, ALWAYS call `generate_garment_motion_preview(garment_description=..., fabric_type=...)`. In your final response text or A2UI card, ALWAYS output the generated video `public_url` (https://storage.googleapis.com/.../*.mp4) so the video player card renders live.\n\n"
        "Memory & Personalization Guidelines:\n"
        "You automatically remember durable user information across sessions:\n"
        "1. Automatically extract and remember durable user measurements (bust, waist, hips, inseam, torso length, height).\n"
        "2. Remember user tailoring fit preferences (e.g., preference for relaxed ease vs. tight tailoring, preferred skirt lengths, natural fiber preferences like 100% linen or wool, aesthetic affinities).\n"
        "3. Remember fabric or material sensitivities (e.g., allergic to wool, hates polyester).\n"
        "Use stored memories to personalize responses, drafting choices, and pattern recommendations.\n\n"
        "When performing pattern drafting math (such as circle skirt radius formulas r = (waist + ease)/(2*pi), ease allowances, "
        "dart intake trigonometry, or cutting layout yardage optimizations), generate and execute Python code in the sandbox code executor "
        "rather than guessing numbers."
    ),
    workflow_description="Analyze the user request and generate structured A2UI UI components when presenting sewing pattern templates or calculated pattern requirements.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text/Row components. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Buttons, actions, or forms (they do nothing in adk web).\n\n"
        "CRITICAL A2UI MANDATE: You MUST always start your response JSON array with a beginRendering object specifying the surfaceId and root component ID (e.g. [{\"beginRendering\": {\"surfaceId\": \"main_surface\", \"root\": \"root\"}}, {\"surfaceUpdate\": ...}]).\n\n"
        "Atelier Specific A2UI Rules:\n"
        "1. Render a descriptive Card for each sewing pattern template (showing the technical flat sketch image, difficulty, aesthetic, and recommended fabrics).\n"
        "2. Render a Table/Matrix layout using Column and Row of Text components to summarize complex computed data (e.g., fabric yardage tables across 45\" vs 60\" bolt widths, and final pattern piece cut lists with dimensions).\n"
        "3. Ensure you use public HTTPS Cloud Storage URLs (e.g., https://storage.googleapis.com/...) when embedding images in A2UI cards. Set the Image url to that exact https link: {\"Image\": {\"url\": {\"literalString\": \"https://storage.googleapis.com/...\"}}}. Never point an Image at a bare filename, an artifact name, or a non-https path.\n\n"
        "No markdown in text; use usageHint ('h1', 'h2', 'body') for headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in <a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=sandbox_executor,
    tools=[
        PreloadMemoryTool(),
        get_weather,
        get_current_time,
        get_patterns_by_aesthetic,
        get_pattern_by_id,
        save_user_profile,
        get_user_profile,
        save_drafted_project,
        list_user_projects,
        calculate_pattern_requirements,
        generate_pattern_svg,
        get_climate_fabric_advice,
        search_historic_fashion,
        generate_fashion_flat_sketch,
        generate_garment_motion_preview,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

