// Title: MASA / StyleGenie Main Script (with segmentation replace-first)
document.addEventListener('DOMContentLoaded', () => {
  const API_ENDPOINT = '/main/generate/';
  const CROP_ENDPOINT = '/main/segment_shirt/';     // NEW

  const form = document.getElementById('generateForm');
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('imageInput');
  const preview = document.getElementById('previewContainer');

  const resultArea = document.getElementById('resultArea');
  const emptyState = document.getElementById('emptyState');
  const resultImage = document.getElementById('resultImage');
  const resultPrompt = document.getElementById('resultPrompt');
  const loadingSkeleton = document.getElementById('loadingSkeleton');
  const downloadBtn = document.getElementById('downloadBtn');

  const imageModal = document.getElementById('imageModal');
  const zoomedImage = document.getElementById('zoomedImage');

  const cropBtn = document.getElementById('cropBtn'); // NEW

  let selected = [];

  function renderPreviews() {
    preview.innerHTML = '';
    dropzone.classList.toggle('has-files', selected.length > 0);

    selected.forEach((file, idx) => {
      const reader = new FileReader();
      reader.onload = e => {
        const wrap = document.createElement('div');
        wrap.className = 'preview-wrapper';

        const img = document.createElement('img');
        img.src = e.target.result;
        img.alt = `upload ${idx+1}`;
        img.addEventListener('click', (ev) => {
          ev.stopPropagation();
          zoomedImage.src = img.src;
          imageModal.style.display = 'flex';
        });
        wrap.appendChild(img);

        const x = document.createElement('button');
        x.type = 'button';
        x.className = 'remove-btn';
        x.textContent = '×';
        x.addEventListener('click', (ev) => {
          ev.stopPropagation();
          selected.splice(idx, 1);
          renderPreviews();
        });
        wrap.appendChild(x);

        // small badge if cropped (inferred by filename)
        if (file.name && /cropped_/i.test(file.name)) {
          const badge = document.createElement('span');
          badge.className = 'badge';
          badge.textContent = 'CROPPED';
          wrap.appendChild(badge);
        }

        preview.appendChild(wrap);
      };
      reader.readAsDataURL(file);
    });
  }

  function addFiles(files) {
    if (!files || !files.length) return;
    const room = Math.max(0, 4 - selected.length);
    const imgs = Array.from(files).slice(0, room).filter(f => f.type.startsWith('image/'));
    selected = selected.concat(imgs);
    renderPreviews();
  }

  // Make the whole rectangle open the file dialog (except when clicking on a preview/remove)
  dropzone.addEventListener('click', (e) => {
    if (e.target.closest('.preview-wrapper') || e.target.closest('.remove-btn')) return;
    fileInput.click();
  });

  fileInput.addEventListener('change', e => addFiles(e.target.files));

  ['dragenter','dragover'].forEach(evt =>
    dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add('is-dragover'); })
  );
  ['dragleave','drop'].forEach(evt =>
    dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.remove('is-dragover'); })
  );
  dropzone.addEventListener('drop', e => addFiles(e.dataTransfer.files));

  imageModal.addEventListener('click', () => imageModal.style.display = 'none');

  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return m ? decodeURIComponent(m[2]) : null;
  }

  function showLoading(promptText) {
    emptyState.style.display = 'none';
    resultArea.style.display = 'block';
    loadingSkeleton.style.display = 'flex';
    resultImage.src = '';
    resultPrompt.textContent = promptText || 'Generating outfit…';
    downloadBtn.style.display = 'none';
  }

  function showResult(imageUrl, promptText) {
    loadingSkeleton.style.display = 'none';
    resultImage.src = imageUrl || '';
    resultPrompt.textContent = promptText || '';
    downloadBtn.href = imageUrl || '#';
    downloadBtn.style.display = imageUrl ? 'inline-block' : 'none';
  }

  // NEW: Crop (segment) and REPLACE selected[0]
  cropBtn.addEventListener('click', async () => {
    if (selected.length === 0) {
      alert('Please upload a shirt image first.');
      return;
    }

    const fd = new FormData();
    fd.append('image', selected[0]);        // only first image

    cropBtn.disabled = true;
    const originalText = cropBtn.textContent;
    cropBtn.textContent = 'Cropping…';

    try {
      const res = await fetch(CROP_ENDPOINT, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
        body: fd,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // fetch the returned PNG and turn it into a File so it behaves like an upload
      const blob = await fetch(data.segmented_url, { cache: 'no-store' }).then(r => r.blob());
      const croppedFile = new File([blob], `cropped_${Date.now()}.png`, { type: 'image/png' });

      // replace first slot and re-render
      selected[0] = croppedFile;
      renderPreviews();
    } catch (err) {
      console.error(err);
      alert('Segmentation failed. Please try again.');
    } finally {
      cropBtn.disabled = false;
      cropBtn.textContent = originalText;
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const fd = new FormData();
    selected.forEach(file => fd.append('image', file));
    fd.append('prompt', form.elements['prompt'].value || '');
    fd.append('style_tag', form.elements['style_tag'].value || '');

    showLoading('Generating outfit…');

    try {
      const res = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
        body: fd,
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const promptUsed = data.prompt_used || fd.get('prompt') || '';
      const urls = Array.isArray(data.generated_image_url) ? data.generated_image_url : [];
      const firstUrl = urls.length ? urls[urls.length - 1] : '';

      showResult(firstUrl, promptUsed);
    } catch (err) {
      console.error(err);
      showResult('', 'Generation failed');
      resultPrompt.textContent = 'Generation failed. Please try again.';
    }
  });
});
