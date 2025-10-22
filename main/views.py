# Title: MASA / Django Views (Generation + Segmentation)
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

# --- NEW: deps for segmentation ---
from PIL import Image
try:
    from ultralytics import YOLO
except Exception:
    YOLO = None  # fail-safe so server can still boot without the lib


# ---------------------------
# Auth + basic pages
# ---------------------------

def login_page(request):
    return render(request, 'login_page.html')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Account created successfully! You are now logged in.")
            login(request, user)
            return redirect('/main/login_page/')
        else:
            print(form.errors.as_json())
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


# ---------------------------
# UNO-FLUX outfit generation
# ---------------------------

@login_required
def generate_outfit(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed."}, status=405)

    prompt_text = request.POST.get("prompt", "") or ""
    tag = request.POST.get("style_tag", "") or ""
    images = request.FILES.getlist("image")

    if not images:
        return JsonResponse({"error": "No images uploaded."}, status=400)

    images = images[:4]
    uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)

    uploaded_paths = []
    for i, img in enumerate(images):
        safe_name = f"{datetime.datetime.now().timestamp():.0f}_{i}_{img.name}"
        local_path = os.path.join(uploads_dir, safe_name)
        with open(local_path, 'wb+') as f:
            for chunk in img.chunks():
                f.write(chunk)
        uploaded_paths.append(local_path)

    final_prompt = get_final_prompt(prompt_text, tag)

    def safe_image(index: int):
        try:
            return handle_file(uploaded_paths[index])
        except IndexError:
            return None

    try:
        hf_token = getattr(settings, 'HF_TOKEN', None) or os.getenv('HF_TOKEN')
        client = Client("bytedance-research/UNO-FLUX", hf_token=hf_token)
        result = client.predict(
            prompt=final_prompt, width=512, height=512, guidance=4, num_steps=25, seed=-1,
            image_prompt1=safe_image(0),
            image_prompt2=safe_image(1),
            image_prompt3=safe_image(2),
            image_prompt4=safe_image(3),
            api_name="/gradio_generate"
        )

        source_generated_path = result[0]
        generated_dir = os.path.join(settings.MEDIA_ROOT, 'generated')
        os.makedirs(generated_dir, exist_ok=True)
        output_filename = f"generated_{datetime.datetime.now().timestamp():.0f}.webp"
        output_path = os.path.join(generated_dir, output_filename)
        shutil.copy(source_generated_path, output_path)

    except Exception as e:
        print("[ERROR] Exception occurred during generation:")
        traceback.print_exc()
        return JsonResponse({"error": f"Hugging Face API failed: {str(e)}"}, status=500)

    rel_url = f"{settings.MEDIA_URL}generated/{output_filename}"
    abs_url = request.build_absolute_uri(rel_url)

    return JsonResponse({
        "prompt_used": final_prompt,
        "uploaded_image_path": uploaded_paths[0],
        "image_url": abs_url,
        "generated_image_url": [abs_url],
    })


# ---------------------------
# NEW: Shirt segmentation API
# ---------------------------

def _get_seg_model():
    from ultralytics import YOLO
    if getattr(settings, '_SEG_MODEL', None) is not None:
        return settings._SEG_MODEL, None
    model_path = str(getattr(settings, 'SEG_MODEL_PATH', os.path.join(settings.BASE_DIR, 'models', 'best.pt')))
    if not os.path.exists(model_path):
        return None, f"Model file not found at: {model_path}"
    try:
        m = YOLO(model_path)
        settings._SEG_MODEL = m
        return m, None
    except Exception as e:
        traceback.print_exc()
        return None, f"Failed to load YOLO model: {repr(e)}"

@login_required
def segment_shirt(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    # load lazily (uses settings.SEG_MODEL_PATH)
    model, load_err = _get_seg_model()
    if load_err:
        return JsonResponse({"error": load_err}, status=500)

    img_file = request.FILES.get('image')
    if not img_file:
        return JsonResponse({"error": "No image provided"}, status=400)

    try:
        # save input
        up_dir = os.path.join(settings.MEDIA_ROOT, 'seg_uploads')
        os.makedirs(up_dir, exist_ok=True)
        in_path = os.path.join(up_dir, f"{datetime.datetime.now().timestamp():.0f}_{img_file.name}")
        with open(in_path, 'wb+') as f:
            for chunk in img_file.chunks():
                f.write(chunk)

        # run prediction on CPU by default (change SEG_DEVICE to 'cuda:0' if available)
        results = model.predict(
            source=in_path,
            save=False,
            imgsz=640,
            conf=0.5,
            verbose=False,
            device=getattr(settings, 'SEG_DEVICE', 'cpu'),
        )
        if not results:
            return JsonResponse({"error": "No results returned from model"}, status=500)

        r0 = results[0]
        if getattr(r0, 'masks', None) is None or getattr(r0.masks, 'data', None) is None:
            return JsonResponse({"error": "No shirt mask detected (is this a YOLOv8 *seg* model?)"}, status=404)
        if r0.masks.data.shape[0] == 0:
            return JsonResponse({"error": "No shirt mask detected"}, status=404)

        # union all masks -> alpha
        union = r0.masks.data.max(dim=0).values.cpu().numpy()  # (h,w) float [0,1]
        orig = Image.open(in_path).convert("RGBA")
        mask_img = Image.fromarray((union * 255).astype('uint8')).resize(orig.size)
        orig.putalpha(mask_img)

        # tight crop
        bbox = orig.getbbox()
        if bbox:
            orig = orig.crop(bbox)

        out_dir = os.path.join(settings.MEDIA_ROOT, 'segmented')
        os.makedirs(out_dir, exist_ok=True)
        out_name = f"shirt_{datetime.datetime.now().timestamp():.0f}.png"
        out_path = os.path.join(out_dir, out_name)
        orig.save(out_path)

        rel_url = f"{settings.MEDIA_URL}segmented/{out_name}"
        abs_url = request.build_absolute_uri(rel_url)
        return JsonResponse({"segmented_url": abs_url})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": f"Segmentation crashed: {repr(e)}"}, status=500)