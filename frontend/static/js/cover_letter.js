// frontend/static/js/cover-letter.js

document.addEventListener('DOMContentLoaded', function() {
    // Toggle cover letter fields based on refinement type
    const refinementType = document.querySelector('#refinement_type');
    const coverLetterField = document.querySelector('#previous_cover_letter');
    const fileField = document.querySelector('#cover_letter_file');
    
    function toggleCoverLetterFields() {
        const show = refinementType.value !== 'generate';
        coverLetterField.disabled = !show;
        fileField.disabled = !show;
        
        // Clear fields when disabled
        if (!show) {
            coverLetterField.value = '';
            fileField.value = '';
        }
    }
    
    // Initialize and add event listener
    if (refinementType) {
        refinementType.addEventListener('change', toggleCoverLetterFields);
        toggleCoverLetterFields();
    }
    
    // File input validation
    const fileInput = document.querySelector('#cover_letter_file');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            const maxSize = 5 * 1024 * 1024; // 5MB
            
            if (file && file.size > maxSize) {
                alert('File size exceeds 5MB limit. Please choose a smaller file.');
                this.value = '';
            }
            
            // Clear text area if file is selected
            if (file) {
                document.querySelector('#previous_cover_letter').value = '';
            }
        });
    }
    
    // Text area input handler
    const coverLetterTextArea = document.querySelector('#previous_cover_letter');
    if (coverLetterTextArea) {
        coverLetterTextArea.addEventListener('input', function() {
            if (this.value.trim() !== '') {
                document.querySelector('#cover_letter_file').value = '';
            }
        });
    }
});
