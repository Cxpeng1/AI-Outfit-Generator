from django.http import JsonResponse
from .utils.prompt_processor import get_final_prompt
import datetime
import os
from django.shortcuts import render
from gradio_client import Client, handle_file
import shutil
import traceback
# Create your views here.
def login_page(request):
    return render(request, 'login_page.html')
# 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
def generate_outfit(request):
    if request.method == 'POST':
        # Get user input
        prompt_text = request.POST.get("prompt", "")
        tag = request.POST.get("style_tag", "")
        image = request.FILES.get("image")

        # Check if image exists
        if not image:
            return JsonResponse({"error": "No image uploaded."}, status=400)

        # Process prompt
        final_prompt = get_final_prompt(prompt_text, tag)

        # Save uploaded image temporarily (for demo/testing)
        filename = f"{datetime.datetime.now().timestamp()}_{image.name}"
        local_path = os.path.join("media", "uploads", filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb+') as f:
            for chunk in image.chunks():
                f.write(chunk)

        try:
            # Call UNO-FLUX on Hugging Face
            client = Client("bytedance-research/UNO-FLUX", hf_token=" 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")
            result = client.predict(
                prompt=final_prompt,
                width=512,
                height=512,
                guidance=4,
                num_steps=25,
                seed=-1,
                image_prompt1=handle_file(local_path),
                image_prompt2=handle_file(local_path),
                image_prompt3=handle_file(local_path),
                image_prompt4=handle_file(local_path),
                api_name="/gradio_generate"
            )
                # Copy the generated image to media folder so frontend can access it
            output_filename = f"generated_{datetime.datetime.now().timestamp()}.webp"
            output_path = os.path.join("media", "generated", output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy(result[0], output_path)

        except Exception as e:
            print("[ERROR] Exception occurred:")
            traceback.print_exc()  # This shows the real error in the terminal
            return JsonResponse({"error": f"Hugging Face API failed: {str(e)}"}, status=500)

        return JsonResponse({
            "prompt_used": final_prompt,
            "uploaded_image_path": local_path,
            "generated_image_url": f"/media/generated/{output_filename}"
        })
    return JsonResponse({"error": "Only POST method is allowed."}, status=405)