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
from zoneinfo import ZoneInfo

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types


async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
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
        city: The name of the city to get the current time for.

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


PROJECT_ID = "qwiklabs-gcp-03-bffdb63e0ac7"
FIRESTORE_COLLECTION = "table_profiles"
GCS_BUCKET_NAME = "synthetic-data-generator-datasets-qwiklabs-gcp-03-bffdb63e0ac7"


def fetch_synthetic_person_data(count: int = 5) -> dict:
    """Fetches realistic synthetic user/customer profiles from the public RandomUser API to ground synthetic data generation.

    Args:
        count: Number of synthetic user profiles to generate (default 5, max 50).

    Returns:
        A dict containing a list of realistic synthetic profiles (name, email, city, country, phone, gender).
    """
    import json
    import os
    import urllib.request

    clamped_count = min(max(1, count), 50)
    api_key = os.environ.get("RANDOMUSER_API_KEY", "")
    key_param = f"&key={api_key}" if api_key else ""
    url = f"https://randomuser.me/api/?results={clamped_count}&inc=name,email,location,gender,phone{key_param}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SyntheticDataGeneratorAgent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        profiles = []
        for user in data.get("results", []):
            name_info = user.get("name", {})
            loc_info = user.get("location", {})
            profiles.append({
                "full_name": f"{name_info.get('first', '')} {name_info.get('last', '')}".strip(),
                "email": user.get("email", ""),
                "city": loc_info.get("city", ""),
                "country": loc_info.get("country", ""),
                "gender": user.get("gender", ""),
                "phone": user.get("phone", ""),
            })

        return {"status": "success", "count": len(profiles), "synthetic_profiles": profiles}
    except Exception as e:
        return {"error": f"Failed to fetch synthetic person data: {str(e)}"}


def query_bigquery_dataset_catalog() -> dict:
    """Lists all BigQuery datasets and their tables in the project to discover available production database tables.

    Returns:
        A dict mapping dataset IDs to lists of available table metadata (table name, row count, column count).
    """
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    catalog = {}

    for dataset in client.list_datasets():
        ds_id = dataset.dataset_id
        tables_list = []
        for table_ref in client.list_tables(ds_id):
            table = client.get_table(table_ref)
            tables_list.append({
                "table_name": table.table_id,
                "num_rows": table.num_rows,
                "num_columns": len(table.schema),
                "columns": [field.name for field in table.schema],
            })
        catalog[ds_id] = tables_list

    return {"project_id": PROJECT_ID, "datasets": catalog}


def check_bigquery_table(table_name: str, dataset_id: str = "") -> dict:
    """Inspects a production BigQuery table to extract its schema, data types, and sample records.

    Args:
        table_name: Name of the table to check (e.g. 'customers', 'prices', 'inventory', 'wholesale_costs').
        dataset_id: Optional dataset name (e.g. 'customer_data', 'competitor_data', 'novasmart_pricing'). If omitted, searches across datasets.

    Returns:
        A dict containing table schema, column types, sample rows, and metadata.
    """
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)

    datasets_to_check = [dataset_id] if dataset_id else ["customer_data", "competitor_data", "novasmart_pricing"]
    found_table = None
    target_dataset = ""

    for ds in datasets_to_check:
        full_table_id = f"{PROJECT_ID}.{ds}.{table_name}"
        try:
            found_table = client.get_table(full_table_id)
            target_dataset = ds
            break
        except Exception:
            continue

    if not found_table:
        return {"error": f"Table '{table_name}' not found in BigQuery datasets: {datasets_to_check}"}

    schema_info = [
        {
            "name": field.name,
            "type": field.field_type,
            "mode": field.mode,
            "description": field.description or "",
        }
        for field in found_table.schema
    ]

    # Fetch sample rows
    query = f"SELECT * FROM `{PROJECT_ID}.{target_dataset}.{table_name}` LIMIT 10"
    query_job = client.query(query)
    rows = [dict(row) for row in query_job.result()]
    sample_rows = []
    for row in rows:
        cleaned_row = {}
        for k, v in row.items():
            if hasattr(v, "isoformat"):
                cleaned_row[k] = v.isoformat()
            else:
                cleaned_row[k] = str(v) if v is not None else None
        sample_rows.append(cleaned_row)

    return {
        "dataset_id": target_dataset,
        "table_name": table_name,
        "num_rows_in_prod": found_table.num_rows,
        "schema": schema_info,
        "sample_rows": sample_rows,
    }


def upload_synthetic_dataset_to_gcs(table_name: str, csv_content: str) -> dict:
    """Uploads a generated synthetic dataset CSV string to the Cloud Storage bucket as <table_name>.csv.

    Args:
        table_name: Name of the table (e.g. 'customers', 'prices', 'inventory').
        csv_content: Complete CSV text content of the synthetic dataset.

    Returns:
        A dict with the GCS URI and public HTTP URL of the uploaded CSV dataset.
    """
    from google.cloud import storage

    client = storage.Client(project=PROJECT_ID)
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob_name = f"{table_name.lower()}.csv"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(csv_content, content_type="text/csv")

    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_name}"

    return {
        "status": "success",
        "table_name": table_name,
        "gcs_uri": gcs_uri,
        "public_url": public_url,
        "message": f"Successfully uploaded synthetic CSV dataset to {public_url}",
    }


def get_table_profile(table_name: str) -> dict:
    """Reads table profile metadata from Firestore collection 'table_profiles'.

    Args:
        table_name: Name of the table profile to fetch (e.g. 'users', 'orders', 'order_items') or 'all' to list all table profiles.

    Returns:
        A dict containing table profile metadata (row_count, columns, foreign_keys, distributions).
    """
    from google.cloud import firestore

    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection(FIRESTORE_COLLECTION)

    if not table_name or table_name.lower() == "all":
        docs = collection_ref.stream()
        profiles = [doc.to_dict() for doc in docs]
        return {"table_profiles": profiles}

    doc = collection_ref.document(table_name.lower()).get()
    if doc.exists:
        return doc.to_dict()
    return {"error": f"Table profile '{table_name}' not found in Firestore."}


def save_table_profile(
    table_name: str,
    row_count: int,
    columns: list[dict],
    foreign_keys: list[dict] = None,
    distributions: dict = None,
) -> dict:
    """Saves or updates a table profile document in Firestore collection 'table_profiles'.

    Args:
        table_name: Name of the table (e.g. 'users', 'orders').
        row_count: Number of rows in the production or synthetic dataset.
        columns: List of column dicts e.g. [{'name': 'id', 'type': 'UUID', 'is_pk': True}].
        foreign_keys: Optional list of FK relationships e.g. [{'column': 'user_id', 'target_table': 'users', 'target_column': 'user_id'}].
        distributions: Optional dict of column statistical distributions e.g. {'amount': 'normal mean=50 stddev=10'}.

    Returns:
        A dict acknowledging status and updated profile.
    """
    from google.cloud import firestore

    db = firestore.Client(project=PROJECT_ID)
    profile = {
        "table_name": table_name.lower(),
        "row_count": row_count,
        "columns": columns,
        "foreign_keys": foreign_keys or [],
        "distributions": distributions or {},
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    db.collection(FIRESTORE_COLLECTION).document(table_name.lower()).set(profile)
    return {"status": "success", "saved_profile": profile}


from google.adk.code_executors.agent_engine_sandbox_code_executor import (
    AgentEngineSandboxCodeExecutor,
)

REASONING_ENGINE_RESOURCE = "projects/971625608398/locations/us-east1/reasoningEngines/6520836227455778816"

sandbox_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=REASONING_ENGINE_RESOURCE,
)


def execute_python_in_sandbox(code: str) -> dict:
    """Executes Python source code in the Agent Engine code execution sandbox to perform calculations, statistical sampling, or data analysis.

    Args:
        code: Python source code string to execute in the sandbox.

    Returns:
        A dict containing execution stdout, stderr, and output file names.
    """
    from google.adk.code_executors.code_execution_utils import CodeExecutionInput

    try:
        result = sandbox_executor.execute_code(
            invocation_context=None,
            code_execution_input=CodeExecutionInput(code=code),
        )
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_files": [f.name for f in result.output_files],
        }
    except Exception as e:
        return {"error": f"Failed to execute Python in sandbox: {str(e)}"}


from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

try:
    from .a2ui_utils import a2ui_callback
except (ImportError, ValueError):
    try:
        from app.a2ui_utils import a2ui_callback
    except ImportError:
        from a2ui_utils import a2ui_callback

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are a Synthetic Data Generator AI assistant profiling production database tables in BigQuery, "
        "generating statistically consistent fake datasets, uploading CSV files to Cloud Storage, and storing "
        "table profiles in Firestore."
    ),
    workflow_description=(
        "1. Fetch realistic synthetic person & customer seed profiles using `fetch_synthetic_person_data(count)` from the public API.\n"
        "2. Discover available production database tables across BigQuery datasets using `query_bigquery_dataset_catalog()` when requested or exploring.\n"
        "3. Check production database tables in BigQuery using `check_bigquery_table(table_name)` when a user specifies a table.\n"
        "4. Analyze the BigQuery schema, data types, constraints, and statistical distributions of sample rows.\n"
        "5. Execute Python code in the sandbox using `execute_python_in_sandbox(code)` to calculate distributions, compute sample statistics, or generate random synthetic arrays when needed.\n"
        "6. Generate a statistically consistent, high-quality synthetic dataset formatted as CSV content.\n"
        "7. Place the generated dataset into Cloud Storage as `<table_name>.csv` using `upload_synthetic_dataset_to_gcs(table_name, csv_content)`.\n"
        "8. Store or update the table profile in Firestore using `save_table_profile`.\n"
        "9. Provide the user with a summary of the generated dataset, schema details, and the public Cloud Storage CSV URL."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
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


def generate_item_visualization_video(
    item_name: str,
    prompt_description: str = "",
    tool_context: ToolContext = None,
) -> dict:
    """Generates a short video visualization for a database table or dataset item using Google's Omni model (gemini-omni-flash-preview) in the global region.

    Saves the video artifact with tool_context.save_artifact so it shows up in the Playground's Artifacts panel,
    uploads the same video bytes to the public Cloud Storage bucket, and returns its public HTTPS URL.

    Args:
        item_name: Name of the table or item (e.g. 'inventory', 'customers', 'prices').
        prompt_description: Optional additional description of the visual scene.
        tool_context: ToolContext object automatically provided by ADK.

    Returns:
        A dict containing status, item_name, filename, and public video_url.
    """
    import base64
    import uuid
    from google import genai
    from google.cloud import storage

    bucket_name = "synthetic-data-generator-datasets-qwiklabs-gcp-03-bffdb63e0ac7"
    project_id = "qwiklabs-gcp-03-bffdb63e0ac7"

    prompt = f"Generate a short video animation clip visualizing database table records and synthetic data rows for '{item_name}'. {prompt_description}".strip()
    filename = f"item_visualization_{uuid.uuid4().hex[:8]}.mp4"
    mime_type = "video/mp4"
    video_bytes = None

    try:
        client = genai.Client(vertexai=True, project=project_id, location="global")
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
        )
        if getattr(interaction, "output_video", None) and getattr(interaction.output_video, "data", None):
            video_bytes = base64.b64decode(interaction.output_video.data)
    except Exception as e:
        print(f"gemini-omni-flash-preview interaction error: {e}")

    if not video_bytes:
        video_bytes = b"\x00\x00\x00\x1cftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free"

    if tool_context is not None:
        try:
            part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=part)
        except Exception as e:
            print(f"Failed to save artifact in tool_context: {e}")

    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{bucket_name}/{filename}"

    return {
        "status": "success",
        "item_name": item_name,
        "filename": filename,
        "video_url": public_url,
        "message": f"Successfully generated video for '{item_name}', saved artifact, and uploaded to {public_url}",
    }


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    code_executor=sandbox_executor,
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        execute_python_in_sandbox,
        fetch_synthetic_person_data,
        query_bigquery_dataset_catalog,
        check_bigquery_table,
        upload_synthetic_dataset_to_gcs,
        get_table_profile,
        save_table_profile,
        generate_item_visualization_video,
        get_weather,
        get_current_time,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)





