style_prompt_map = {
    "Casual": "Using the cropped shirt shown in the main image, create a full-body image of a casual, gender-neutral outfit that incorporates elements from supporting images 2, 3, and 4. The outfit should be comfortable, stylish, and versatile—suitable for female—with the cropped shirt as the main focus. Ensure the entire outfit is visible from head to toe.",
    "formal": "Using the cropped shirt shown in the main image, create a full-body image of a formal outfit that incorporates elements from supporting images 2, 3, and 4. The look should be elegant, polished, and suitable for a professional or semi-formal setting—styled for female. The model should be shown clearly from head to toe, including formal footwear and lower-body garments, in a refined indoor or clean background setting.",
    "sporty": "Using the cropped shirt shown in the main image, create a full-body image of a sporty, activewear outfit that incorporates elements from supporting images 2, 3, and 4. The outfit should be athletic, comfortable, and functional—suitable for female—and styled for activities like gym workouts, running, or casual sports. Make sure the model is shown fully from head to toe, including athletic shoes and sporty lower-body garments, in an active or outdoor setting",
    "business": "a business outfit",
    "party": "Using the cropped shirt shown in the main image, create a full-body image of a stylish party outfit that incorporates elements from supporting images 2, 3, and 4. The look should be fun, trendy, and clearly suited for an evening or night party—featuring bold accessories, eye-catching shoes, or festive textures. The model should be shown fully from head to toe, standing in a vibrant, party-themed setting, with shoes and lower-body garments clearly visible.",
    "vintage": "a vintage outfit",
    "bohemian": "a bohemian outfit",
    "streetwear": "a streetwear outfit",
}
# build prompts for outfit generation based on user input and selected tags.
def build_prompt(tag: str, item_type: str = "shirt") -> str: # shirt as default
    base = style_prompt_map.get(tag, "")
    return f"Generate an outfit to match this {item_type}, featuring {base}."

def get_final_prompt(user_text: str, selected_tag: str) -> str:
    if user_text.strip():
        return user_text.strip()
    return build_prompt(selected_tag)



