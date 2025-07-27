document.addEventListener("DOMContentLoaded", function () {
    const imageInput = document.getElementById("imageInput");
    const previewContainer = document.getElementById("previewContainer");
    const imageModal = document.getElementById("imageModal");
    const zoomedImage = document.getElementById("zoomedImage");
    const form = document.getElementById("generateForm");

    let selectedImages = [];

    function updatePreviews() {
      previewContainer.innerHTML = "";

      selectedImages.forEach((file, index) => {
        const reader = new FileReader();
        reader.onload = function (e) {
          const wrapper = document.createElement("div");
          wrapper.className = "preview-wrapper";

          const img = document.createElement("img");
          img.src = e.target.result;
          img.style.maxWidth = "80px";

          img.addEventListener("click", () => {
            zoomedImage.src = img.src;
            imageModal.style.display = "flex";
          });

          const removeBtn = document.createElement("span");
          removeBtn.textContent = "×";
          removeBtn.className = "remove-btn";
          removeBtn.addEventListener("click", () => {
            selectedImages.splice(index, 1);
            updatePreviews();
          });

          wrapper.appendChild(img);
          wrapper.appendChild(removeBtn);
          previewContainer.appendChild(wrapper);
        };
        reader.readAsDataURL(file);
      });

      const dataTransfer = new DataTransfer();
      selectedImages.forEach(file => dataTransfer.items.add(file));
      imageInput.files = dataTransfer.files;
    }

    imageInput.addEventListener("change", function () {
      const newFiles = Array.from(imageInput.files);
      selectedImages = selectedImages.concat(newFiles);

      const fileMap = new Map();
      selectedImages.forEach(file => fileMap.set(file.name, file));
      selectedImages = Array.from(fileMap.values());

      if (selectedImages.length > 4) {
        alert("You can only upload up to 4 images.");
        selectedImages = selectedImages.slice(0, 4);
      }

      updatePreviews();
    });

    imageModal.addEventListener("click", function (e) {
      if (e.target === imageModal) {
        imageModal.style.display = "none";
        zoomedImage.src = "";
      }
    });

    form.addEventListener("submit", async function (e) {
      e.preventDefault();

      document.getElementById("resultArea").style.display = "block";
      document.getElementById("resultPrompt").textContent = "Generating outfit...";
      document.getElementById("resultImage").style.display = "none";
      document.getElementById("downloadBtn").style.display = "none";

      const formData = new FormData(form);
      const response = await fetch("/main/generate/", {
        method: "POST",
        body: formData,
        headers: {
          "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value
        }
      });

      const data = await response.json();

      if (data.error) {
        alert("Error: " + data.error);
      } else {
        document.getElementById("resultPrompt").textContent = data.prompt_used;
        document.getElementById("resultImage").src = data.generated_image_url;
        document.getElementById("resultImage").style.display = "block";
        document.getElementById("downloadBtn").href = data.generated_image_url;
        document.getElementById("downloadBtn").style.display = "inline-block";
      }
    });
});