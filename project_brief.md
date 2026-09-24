# My agent: Smart Pantry Recipe Concierge

One-liner: A conversational recipe assistant that helps home cooks discover meals using on-hand ingredients, manage dietary preferences, and save favorite recipes.

Tool coverage:
- Memory: Remembers user's dietary preferences, allergies, household size, and cooking skill level across sessions.
- Tools:
  - `search_recipes`: Finds recipe matches based on available ingredients and dietary constraints.
  - `save_favorite_recipe`: Saves a recipe to the user's personal cookbook in Firestore.
  - `get_saved_recipes`: Retrieves the user's saved favorite recipes.
- Catalog/UI: Recipe collection (rendered with rich A2UI cards displaying ingredients, prep time, instructions, and tags).
- Image gen: Generates appetizing dish imagery for custom or recommended recipes.
- Sandbox: Performs ingredient scaling calculations and nutrition unit conversions.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch: Code sandbox for recipe scaling/nutrition calculations, Firestore recipe database integration.
