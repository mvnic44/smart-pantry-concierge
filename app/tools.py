"""Firestore & Storage tools for Smart Pantry Recipe Concierge."""

import uuid
from typing import List, Optional
from google import genai
from google.genai import types
from google.cloud import firestore, storage
from google.adk.tools import ToolContext
from google.adk.memory.memory_entry import MemoryEntry

# CRITICAL: Hardcode project ID and bucket name as strings (do NOT read from env)
FIRESTORE_PROJECT = "qwiklabs-gcp-02-47994b847bd6"
GCS_BUCKET_NAME = "smart-pantry-recipes-qwiklabs-gcp-02-47994b847bd6"

_db = None
_storage_client = None
_genai_client = None

def get_firestore_client() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=FIRESTORE_PROJECT)
    return _db

def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client(project=FIRESTORE_PROJECT)
    return _storage_client

def get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(
            vertexai=True,
            location="global",
            project=FIRESTORE_PROJECT,
        )
    return _genai_client

def search_recipes(ingredients: Optional[List[str]] = None, dietary_tag: Optional[str] = None) -> List[dict]:
    """Search recipes in the database based on available ingredients or dietary tags.

    Args:
        ingredients: Optional list of ingredient names on hand (e.g. ["tomatoes", "garlic"]).
        dietary_tag: Optional dietary tag to filter by (e.g. "vegan", "gluten-free", "quick").

    Returns:
        List of matching recipe dictionaries with titles, ingredients, instructions, and prep times.
    """
    db = get_firestore_client()
    recipes_ref = db.collection("recipes")
    docs = recipes_ref.stream()

    results = []
    for doc in docs:
        data = doc.to_dict()
        data["recipe_id"] = doc.id
        
        if dietary_tag:
            tags = [t.lower() for t in data.get("dietary_tags", [])]
            if dietary_tag.lower() not in tags:
                continue

        if ingredients:
            recipe_ingredients = [i.lower() for i in data.get("ingredients", [])]
            matched_count = 0
            for user_ing in ingredients:
                if any(user_ing.lower() in ring for ring in recipe_ingredients):
                    matched_count += 1
            if matched_count == 0:
                continue
            data["matched_ingredient_count"] = matched_count

        results.append(data)

    if ingredients and results:
        results.sort(key=lambda x: x.get("matched_ingredient_count", 0), reverse=True)

    return results

def save_favorite_recipe(recipe_id: str) -> str:
    """Mark a recipe as a favorite in the saved cookbook.

    Args:
        recipe_id: The ID of the recipe to favorite (e.g. "r1").

    Returns:
        Confirmation message.
    """
    db = get_firestore_client()
    doc_ref = db.collection("recipes").document(recipe_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return f"Error: Recipe with ID '{recipe_id}' not found."

    doc_ref.update({"is_favorite": True})
    recipe_title = doc.to_dict().get("title", recipe_id)
    return f"Successfully saved '{recipe_title}' (ID: {recipe_id}) to your favorite recipes!"

def get_favorite_recipes() -> List[dict]:
    """Retrieve all saved favorite recipes from the personal cookbook.

    Returns:
        List of favorite recipe dictionaries.
    """
    db = get_firestore_client()
    docs = db.collection("recipes").where("is_favorite", "==", True).stream()

    favorites = []
    for doc in docs:
        data = doc.to_dict()
        data["recipe_id"] = doc.id
        favorites.append(data)

    return favorites

def scale_recipe_servings(recipe_id: str, target_servings: int) -> dict:
    """Scale a recipe's ingredient proportions based on target number of servings.

    Args:
        recipe_id: The ID of the recipe to scale (e.g. "r1").
        target_servings: Desired number of servings (e.g. 4 or 6).

    Returns:
        Dictionary with scaled recipe information including title, original vs target servings, scale factor, and ingredient notes.
    """
    db = get_firestore_client()
    doc_ref = db.collection("recipes").document(recipe_id)
    doc = doc_ref.get()

    if not doc.exists:
        return {"error": f"Recipe with ID '{recipe_id}' not found."}

    data = doc.to_dict()
    original_servings = data.get("servings", 1)
    if original_servings <= 0:
        original_servings = 1

    scale_factor = round(target_servings / original_servings, 2)
    ingredients = data.get("ingredients", [])

    return {
        "recipe_id": recipe_id,
        "title": data.get("title", ""),
        "original_servings": original_servings,
        "target_servings": target_servings,
        "scale_factor": scale_factor,
        "ingredients": ingredients,
        "scaling_note": f"Multiply all original ingredient quantities by {scale_factor}x for {target_servings} servings.",
        "instructions": data.get("instructions", [])
    }

def generate_recipe_image(recipe_title: str, description: Optional[str] = None, tool_context: Optional[ToolContext] = None) -> dict:
    """Generate an appetizing dish image for a recipe using gemini-3.1-flash-lite-image in the global region.

    Saves the image as an ADK artifact and uploads it to the public Cloud Storage bucket.

    Args:
        recipe_title: Title of the dish (e.g. "Garlic Butter Tomato Pasta").
        description: Optional details about the dish presentation or ingredients.
        tool_context: Context object supplied by ADK runtime.

    Returns:
        Dictionary containing the generated image's public HTTP URL and status.
    """
    prompt = f"A professional high-resolution food photography shot of {recipe_title}."
    if description:
        prompt += f" {description}"

    client = get_genai_client()
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE", "TEXT"]
        )
    )

    image_bytes = None
    mime_type = "image/jpeg"

    if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                if part.inline_data.mime_type:
                    mime_type = part.inline_data.mime_type
                break

    if not image_bytes:
        return {"error": "Failed to generate image bytes from model response."}

    ext = "jpg" if "jpeg" in mime_type else "png"
    safe_title = "".join(c if c.isalnum() else "_" for c in recipe_title.lower()).strip("_")
    filename = f"{safe_title}_{uuid.uuid4().hex[:6]}.{ext}"

    if tool_context:
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception as e:
            print(f"Warning: Failed to save artifact in tool_context: {e}")

    storage_cli = get_storage_client()
    bucket = storage_cli.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"

    return {
        "status": "success",
        "recipe_title": recipe_title,
        "filename": filename,
        "public_url": public_url,
    }

async def save_user_preference(
    preference_type: str,
    details: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Save user dietary preferences, allergies, or restrictions to long-term memory bank.

    Args:
        preference_type: Category of preference (e.g. "allergy", "dietary_preference", "disliked_ingredient").
        details: Specific preference detail (e.g. "Peanut allergy", "Follows vegan diet", "Dislikes cilantro").
        tool_context: Context object supplied by ADK runtime.

    Returns:
        Confirmation message.
    """
    memory_text = f"User Dietary Preference/Allergy [{preference_type}]: {details}"

    if tool_context:
        app_name = getattr(tool_context, "app_name", "app") or "app"
        user_id = getattr(tool_context, "user_id", "user") or "user"
        print(f"[MEMORY LOG] save_user_preference: app_name='{app_name}', user_id='{user_id}'", flush=True)

        entry = MemoryEntry(
            content=types.Content(
                parts=[types.Part.from_text(text=memory_text)]
            )
        )
        try:
            await tool_context.add_memory(memories=[entry])
        except Exception as e:
            print(f"Warning: tool_context.add_memory failed: {e}", flush=True)

        # Fallback/explicit save to ('app', 'user') to ensure cross-session & cross-client persistence
        if (app_name, user_id) != ("app", "user"):
            try:
                inv_ctx = getattr(tool_context, "_invocation_context", None)
                mem_service = getattr(inv_ctx, "memory_service", None) if inv_ctx else None
                if mem_service:
                    await mem_service.add_memory(
                        app_name="app",
                        user_id="user",
                        memories=[entry]
                    )
            except Exception as e:
                print(f"Warning: Explicit memory_service.add_memory failed: {e}", flush=True)

    return f"Successfully recorded in long-term memory bank: '{memory_text}'"

async def load_user_preferences(
    query: str,
    tool_context: Optional[ToolContext] = None,
) -> dict:
    """Retrieve saved user dietary preferences, allergies, and restrictions from long-term memory.

    Args:
        query: Query term to search in memory (e.g. "allergies", "diet", "peanuts", "vegan").
        tool_context: Context object supplied by ADK runtime.

    Returns:
        Dictionary of matching memory entries.
    """
    memories = []
    if tool_context:
        app_name = getattr(tool_context, "app_name", "app") or "app"
        user_id = getattr(tool_context, "user_id", "user") or "user"
        print(f"[MEMORY LOG] load_user_preferences: app_name='{app_name}', user_id='{user_id}', query='{query}'", flush=True)

        # 1. Search using session/tool_context scope
        try:
            resp = await tool_context.search_memory(query)
            if hasattr(resp, "memories") and resp.memories:
                memories.extend(resp.memories)
        except Exception as e:
            print(f"Warning: tool_context.search_memory failed: {e}", flush=True)

        # 2. Search under fixed ('app', 'user') scope to guarantee cross-session retrieval
        if (app_name, user_id) != ("app", "user") or not memories:
            try:
                inv_ctx = getattr(tool_context, "_invocation_context", None)
                mem_service = getattr(inv_ctx, "memory_service", None) if inv_ctx else None
                if mem_service:
                    resp = await mem_service.search_memory(
                        app_name="app",
                        user_id="user",
                        query=query,
                    )
                    if hasattr(resp, "memories") and resp.memories:
                        # Append unique memories
                        existing_facts = set()
                        for m in memories:
                            if hasattr(m, "content") and m.content and m.content.parts:
                                for p in m.content.parts:
                                    if hasattr(p, "text"):
                                        existing_facts.add(p.text)
                        for m in resp.memories:
                            if hasattr(m, "content") and m.content and m.content.parts:
                                for p in m.content.parts:
                                    if hasattr(p, "text") and p.text not in existing_facts:
                                        memories.append(m)
            except Exception as e:
                print(f"Warning: Fixed scope search_memory failed: {e}", flush=True)

    results = []
    for m in memories:
        if hasattr(m, "content") and m.content and hasattr(m.content, "parts"):
            for part in m.content.parts:
                if hasattr(part, "text") and part.text:
                    results.append(part.text)

    return {"query": query, "found_memories": results}
