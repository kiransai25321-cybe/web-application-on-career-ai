// AI Resume Analyzer client-side interactions

document.addEventListener('DOMContentLoaded', () => {
  // Password toggle
  const toggleButtons = document.querySelectorAll('.toggle-password-btn');
  toggleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (input) {
        if (input.type === 'password') {
          input.type = 'text';
          btn.innerHTML = `<svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18"/></svg>`;
        } else {
          input.type = 'password';
          btn.innerHTML = `<svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>`;
        }
      }
    });
  });

  // Drag and Drop Resume Uploader
  const dropZone = document.getElementById('resume-drop-zone');
  const fileInput = document.getElementById('resume-file-input');
  const filePreview = document.getElementById('selected-file-preview');
  const fileNameDisplay = document.getElementById('selected-file-name');
  const fileSizeDisplay = document.getElementById('selected-file-size');
  const uploadForm = document.getElementById('resume-upload-form');
  const uploadLoading = document.getElementById('upload-loading-overlay');
  const uploadError = document.getElementById('upload-error-msg');

  if (dropZone && fileInput) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('drop-zone-active');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('drop-zone-active');
      }, false);
    });

    dropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length > 0) {
        handleFileSelection(files[0]);
      }
    });

    dropZone.addEventListener('click', () => {
      fileInput.click();
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        handleFileSelection(fileInput.files[0]);
      }
    });
  }

  function handleFileSelection(file) {
    if (uploadError) uploadError.classList.add('hidden');

    const validExtensions = ['.pdf', '.docx'];
    const fileName = file.name.toLowerCase();
    const isValidExt = validExtensions.some(ext => fileName.endsWith(ext));

    if (!isValidExt) {
      showError('Please upload a valid PDF (.pdf) or Word document (.docx).');
      return;
    }

    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      showError('File exceeds 5MB limit. Please upload a smaller file.');
      return;
    }

    // Set file input files
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;

    // Show preview
    if (filePreview && fileNameDisplay && fileSizeDisplay) {
      fileNameDisplay.textContent = file.name;
      const sizeKB = (file.size / 1024).toFixed(1);
      fileSizeDisplay.textContent = `${sizeKB} KB`;
      filePreview.classList.remove('hidden');
    }
  }

  function showError(msg) {
    if (uploadError) {
      uploadError.textContent = msg;
      uploadError.classList.remove('hidden');
    } else {
      alert(msg);
    }
  }

  // Form submission with loading indicator
  if (uploadForm) {
    uploadForm.addEventListener('submit', (e) => {
      if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        e.preventDefault();
        showError('Please select or drop a resume file first.');
        return;
      }
      if (uploadLoading) {
        uploadLoading.classList.remove('hidden');
      }
    });
  }
});
