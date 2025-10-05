import os
import datetime
import shutil
import traceback

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm

from gradio_client import Client, handle_file

from .utils.prompt_processor import get_final_prompt


# ---------------------------
# Auth + basic pages
# ---------------------------

def login_page(request):
    """
    Render the login page (do NOT require login here).
    Your URLs should route the built-in LoginView to this template or
    you can post to /accounts/login/ depending on your setup.
    """
    return render(request, 'login_page.html')


def register(request):
    """
    Simple registration view using Django's built-in UserCreationForm.
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Account created successfully! You are now logged in.")
            login(request, user)
            # redirect to your app home after signup
            return redirect('/main/login_page/')
        else:
            # Useful during development
            print(form.errors.as_json())
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


# ---------------------------
# Outfit generation endpoint
# ---------------------------

@login_required  # optional: remove if you want it public
def generate_outfit(request):
    """
    Accepts POST with:
      - prompt (str)
      - style_tag (str)
      - image (up to 4 files)

    Saves uploads under MEDIA_ROOT/uploads, calls UNO-FLUX,
    copies result into MEDIA_ROOT/generated, and returns JSON with
    an absolute image URL so the browser can load it directly.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed."}, status=405)

    prompt_text = request.POST.get("prompt", "") or ""
    tag = request.POST.get("style_tag", "") or ""
    images = request.FILES.getlist("image")

    if not images:
        return JsonResponse({"error": "No images uploaded."}, status=400)

    # Limit to 4 images
    images = images[:4]

    # Ensure upload dir exists
    uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    # Persist uploads to disk
    uploaded_paths = []
    for i, img in enumerate(images):
        safe_name = f"{datetime.datetime.now().timestamp():.0f}_{i}_{img.name}"
        local_path = os.path.join(uploads_dir, safe_name)
        with open(local_path, 'wb+') as f:
            for chunk in img.chunks():
                f.write(chunk)
        uploaded_paths.append(local_path)

    # Build the final prompt the same way as before
    final_prompt = get_final_prompt(prompt_text, tag)

    # Helper to safely pass image files into gradio_client
    def safe_image(index: int):
        try:
            return handle_file(uploaded_paths[index])
        except IndexError:
            return None

    try:
        # Prefer env/settings token rather than hardcoding
        hf_token = getattr(settings, 'HF_TOKEN', None) or os.getenv('HF_TOKEN')
        client = Client("bytedance-research/UNO-FLUX", hf_token=hf_token)

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

        # result is typically a list of file paths; use the first
        source_generated_path = result[0]

        # Ensure generated dir exists under MEDIA
        generated_dir = os.path.join(settings.MEDIA_ROOT, 'generated')
        os.makedirs(generated_dir, exist_ok=True)

        # Copy to our MEDIA folder with a unique name
        output_filename = f"generated_{datetime.datetime.now().timestamp():.0f}.webp"
        output_path = os.path.join(generated_dir, output_filename)
        shutil.copy(source_generated_path, output_path)

    except Exception as e:
        print("[ERROR] Exception occurred during generation:")
        traceback.print_exc()
        return JsonResponse({"error": f"Hugging Face API failed: {str(e)}"}, status=500)

    # Build a browser-reachable URL: /media/generated/xxx.webp
    rel_url = f"{settings.MEDIA_URL}generated/{output_filename}"           # '/media/generated/...'
    abs_url = request.build_absolute_uri(rel_url)                          # 'http://host:port/media/...'

    # Respond with BOTH a single string and an array for robust frontends
    return JsonResponse({
        "prompt_used": final_prompt,
        # This is a filesystem path (useful for debugging), not a web URL:
        "uploaded_image_path": uploaded_paths[0],
        # Preferred keys for the frontend:
        "image_url": abs_url,
        "generated_image_url": [abs_url],
    })
