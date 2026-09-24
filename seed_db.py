"""Seed script to populate initial recipes into Firestore for Smart Pantry Recipe Concierge."""

from google.cloud import firestore

# CRITICAL: Hardcode project ID as string (do NOT use GOOGLE_CLOUD_PROJECT env var)
FIRESTORE_PROJECT = "qwiklabs-gcp-02-47994b847bd6"

db = firestore.Client(project=FIRESTORE_PROJECT)

RECIPES = [
    {
        "recipe_id": "r1",
        "title": "Garlic Butter Tomato Pasta",
        "ingredients": ["pasta", "tomatoes", "garlic", "butter", "parmesan", "basil"],
        "instructions": [
            "Boil pasta in salted water until al dente.",
            "Sauté minced garlic and diced tomatoes in butter.",
            "Toss pasta into garlic butter sauce and top with fresh basil and parmesan."
        ],
        "prep_time_minutes": 20,
        "dietary_tags": ["vegetarian", "quick"],
        "is_favorite": True,
        "servings": 2,
    },
    {
        "recipe_id": "r2",
        "title": "Avocado & Chickpea Salad",
        "ingredients": ["chickpeas", "avocado", "cucumber", "lemon", "olive oil", "parsley"],
        "instructions": [
            "Rinse and drain chickpeas.",
            "Dice avocado and cucumber.",
            "Whisk lemon juice and olive oil with salt and pepper.",
            "Combine all ingredients in a bowl and toss gently."
        ],
        "prep_time_minutes": 15,
        "dietary_tags": ["vegan", "gluten-free", "quick", "healthy"],
        "is_favorite": False,
        "servings": 2,
    },
    {
        "recipe_id": "r3",
        "title": "Classic Vegetable Stir Fry",
        "ingredients": ["broccoli", "carrots", "bell pepper", "soy sauce", "ginger", "sesame oil", "rice"],
        "instructions": [
            "Cook rice according to package directions.",
            "Chop broccoli, carrots, and bell pepper into bite-sized pieces.",
            "Stir fry vegetables with minced ginger in sesame oil over high heat.",
            "Add soy sauce and serve hot over rice."
        ],
        "prep_time_minutes": 25,
        "dietary_tags": ["vegan", "dairy-free"],
        "is_favorite": True,
        "servings": 3,
    },
    {
        "recipe_id": "r4",
        "title": "Spinach & Mushroom Omelette",
        "ingredients": ["eggs", "spinach", "mushrooms", "cheese", "butter", "salt"],
        "instructions": [
            "Whisk eggs with a pinch of salt.",
            "Sauté sliced mushrooms and spinach in butter until tender.",
            "Pour whisked eggs into skillet, fold over vegetables with cheese, and serve."
        ],
        "prep_time_minutes": 10,
        "dietary_tags": ["vegetarian", "gluten-free", "quick", "keto"],
        "is_favorite": False,
        "servings": 1,
    }
]

def seed():
    collection_ref = db.collection("recipes")
    print(f"Seeding {len(RECIPES)} recipes into Firestore collection 'recipes' (project: '{FIRESTORE_PROJECT}')...")
    for recipe in RECIPES:
        doc_ref = collection_ref.document(recipe["recipe_id"])
        doc_ref.set(recipe)
        print(f"  ✓ Added recipe: {recipe['title']} (ID: {recipe['recipe_id']})")
    print("Firestore seeding completed successfully!")

if __name__ == "__main__":
    seed()
