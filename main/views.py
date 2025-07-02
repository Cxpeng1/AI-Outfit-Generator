from django.http import JsonResponse
from .utils.prompt_processor import get_final_prompt
import datetime
import os
from django.shortcuts import render
# Create your views here.
def login_page(request):
    return render(request, 'login_page.html')

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
        save_path = os.path.join("media", "uploads", filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb+') as f:
            for chunk in image.chunks():
                f.write(chunk)

        # Simulate generated image result (be replace later with real API call)
        dummy_result_path = "/static/demo_result.jpg"

        return JsonResponse({
            "prompt_used": final_prompt,
            "uploaded_image_path": save_path,
            "generated_image_url": dummy_result_path
        })

    return JsonResponse({"error": "Only POST method is allowed."}, status=405)