// Resume Upload & AI Processing Logic
function processResume() {
    const fileInput = document.getElementById('resumeUpload');
    const resultsSection = document.getElementById('results');

    if (fileInput.files.length === 0) {
        resultsSection.textContent = "Please upload a resume.";
        return;
    }

    const resumeFile = fileInput.files[0];

    // Simulating AI analysis (Replace with actual backend API)
    setTimeout(() => {
        resultsSection.textContent = "AI Optimization Complete: Resume enhanced for ATS compatibility!";
    }, 2000);
}

// Enhancing UI Interactivity
document.addEventListener("DOMContentLoaded", () => {
    const uploadSection = document.querySelector(".upload-section");

    uploadSection.addEventListener("mouseenter", () => {
        uploadSection.style.transform = "scale(1.05)";
    });

    uploadSection.addEventListener("mouseleave", () => {
        uploadSection.style.transform = "scale(1)";
    });
});
