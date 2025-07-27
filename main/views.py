from django.http import JsonResponse
from .utils.prompt_processor import get_final_prompt
import datetime
import os
from django.shortcuts import render
from gradio_client import Client, handle_file
import shutil
import traceback

def login_page(request):
    return render(request, 'login_page.html')

def generate_outfit(request):
    if request.method == 'POST':
        prompt_text = request.POST.get("prompt", "")
        tag = request.POST.get("style_tag", "")
        images = request.FILES.getlist("image")

        if not images or len(images) == 0:
            return JsonResponse({"error": "No images uploaded."}, status=400)

        images = images[:4]
        image_paths = []

        for i, img in enumerate(images):
            filename = f"{datetime.datetime.now().timestamp()}_{i}_{img.name}"
            local_path = os.path.join("media", "uploads", filename)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb+') as f:
                for chunk in img.chunks():
                    f.write(chunk)
            image_paths.append(local_path)

        final_prompt = get_final_prompt(prompt_text, tag)

        # helper to safely access images
        def safe_image(index):
            try:
                return handle_file(image_paths[index])
            except IndexError:
                return None

        try:
            client = Client("bytedance-research/UNO-FLUX", hf_token="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")
            result = client.predict(
                prompt=final_prompt,
                width=512,
                height=512,
                guidance=4,
                num_steps=25,
                seed=-1,
                image_prompt1=safe_image(0),
                image_prompt2=safe_image(1),
                image_prompt3=safe_image(2),
                image_prompt4=safe_image(3),
                api_name="/gradio_generate"
            )

            output_filename = f"generated_{datetime.datetime.now().timestamp()}.webp"
            output_path = os.path.join("media", "generated", output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.copy(result[0], output_path)

        except Exception as e:
            print("[ERROR] Exception occurred:")
            traceback.print_exc()
            return JsonResponse({"error": f"Hugging Face API failed: {str(e)}"}, status=500)

        return JsonResponse({
            "prompt_used": final_prompt,
            "uploaded_image_path": image_paths[0],  # first image
            "generated_image_url": f"/media/generated/{output_filename}"
        })

    return JsonResponse({"error": "Only POST method is allowed."}, status=405)
