// Mock Interview Specific JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Example: Add character counters or dynamic interactions if needed
    const resumeTextAreas = document.querySelectorAll('textarea[name="answers"], textarea[name="job_description"], textarea[name="resume_text"]');

    resumeTextAreas.forEach(textarea => {
        // You could add event listeners for input, focus, blur, etc.
        // For example, to show a character count:
        // const charCount = document.createElement('div');
        // charCount.classList.add('text-xs', 'text-gray-400', 'mt-1', 'text-right');
        // textarea.parentNode.appendChild(charCount);
        // textarea.addEventListener('input', () => {
        //     charCount.textContent = `${textarea.value.length} characters`;
        // });
    });

    // Example: Confirm before submitting answers
    const answerForm = document.querySelector('form[action*="/answer"]'); // Find form for answering questions
    if (answerForm) {
        answerForm.addEventListener('submit', function(event) {
            const unansweredQuestions = Array.from(answerForm.querySelectorAll('textarea[name="answers"]')).some(ta => ta.value.trim() === "");
            if (unansweredQuestions) {
                if (!confirm('You have some unanswered questions. Are you sure you want to submit?')) {
                    event.preventDefault();
                }
            } else {
                 if (!confirm('Are you sure you want to submit all your answers? You cannot change them later.')) {
                    event.preventDefault();
                }
            }
        });
    }
});
