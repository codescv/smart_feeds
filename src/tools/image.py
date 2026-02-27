import os
import base64
from typing import Optional
import config
from google import genai
from google.genai import types

def generate_image(
    prompt: str,
    output_path: str,
    model_id: Optional[str] = None,
    aspect_ratio: str = "16:9",
    safety_filter_level: str = "block_some",
    person_generation: str = "allow_adult",
) -> Optional[str]:
    """
    Generates an image using Google GenAI and saves it to the output path.
    
    Args:
        prompt: The text prompt for image generation.
        output_path: The file path to save the generated image.
        model_id: The model ID to use (default: env IMAGE_MODEL_ID).
        aspect_ratio: Aspect ratio for the image (e.g., "16:9", "1:1").
        safety_filter_level: Safety filter level.
        person_generation: Person generation setting.
        
    Returns:
        The path to the saved image if successful, None otherwise.
    """
    try:
        if model_id is None:
            model_id = config.get_image_model_id()
            
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
        print(f"Generating image with model: {model_id}")
        print(f"Prompt: {prompt}")
        
        response = client.models.generate_images(
            model=model_id,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                aspect_ratio=aspect_ratio,
                safety_filter_level=safety_filter_level,
                person_generation=person_generation,
            )
        )
        
        if response.generated_images:
            image = response.generated_images[0]
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "wb") as f:
                f.write(image.image.image_bytes)
                
            print(f"Image saved to: {output_path}")
            return output_path
        else:
            print("No image returned by the model.")
            return None
            
    except Exception as e:
        print(f"Error generating image: {e}")
        return None
