// formatter.js

// Global state (potentially)
let globalResumeId = null; // Will be set from Flask data
let currentResumeData = { // Holds the structured data of the resume
    personal: { full_name: "", email: "", phone: "", location: "", linkedin: "", portfolio: "" },
    summary: "",
    experiences: [],
    education: [],
    skills: { technical_skills: "", soft_skills: "", certifications: "" },
    additional: { projects: "", languages: "", volunteer: "" },
    template_settings: { // For storing template choices
        name: "professional", // Default template
        color_scheme: "blue", // Default color
        font_family: "Inter",
        contact_icons: true,
        two_column: false
    }
};
let currentZoomLevel = 1.0;

document.addEventListener('DOMContentLoaded', function() {
    // --- Initialize from Flask Data ---
    const titleInput = document.getElementById('resumeTitleInput');
    const resumeTextarea = document.getElementById('resumeText'); // Main content input for now

    globalResumeId = currentResumeId; // `currentResumeId` is from inline script in HTML

    if (titleInput && initialResumeTitle) {
        titleInput.value = initialResumeTitle;
    }

    if (resumeTextarea && initialResumeContentJsonString) {
        try {
            const parsedContent = JSON.parse(initialResumeContentJsonString);
            currentResumeData = { ...currentResumeData, ...parsedContent }; // Merge with default, preferring loaded data
            // For Phase 1, populate the main textarea with the stringified content for user to see/edit directly
            // A more advanced implementation would populate individual form fields if they existed for each section
            resumeTextarea.value = JSON.stringify(currentResumeData, null, 2);
            updateLastUpdatedTimestamp();
        } catch (e) {
            console.error("Error parsing initial resume content JSON:", e);
            // If parsing fails, it might be plain text from an older resume or malformed
            resumeTextarea.value = initialResumeContentJsonString; // Show raw string
            // Initialize currentResumeData with this raw text if needed for saving
            currentResumeData.raw_text = initialResumeContentJsonString;
        }
    }
    // Initial preview update based on loaded data
    updateLivePreview();


    // --- Event Listeners ---
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileUpload);
    }

    const parseBtn = document.getElementById('parseBtn');
    if (parseBtn) {
        parseBtn.addEventListener('click', handleProcessInput);
    }

    const saveResumeBtn = document.getElementById('saveResumeButton');
    if (saveResumeBtn) {
        saveResumeBtn.addEventListener('click', saveResumeDataToServer);
    }

    if (titleInput) {
        titleInput.addEventListener('input', updateLivePreview); // Update preview on title change
    }
    if (resumeTextarea) {
        resumeTextarea.addEventListener('input', () => {
            // When textarea changes, try to update currentResumeData
            // This is simplistic; a real editor would have structured fields
            try {
                const parsedFromTextarea = JSON.parse(resumeTextarea.value);
                currentResumeData = { ...currentResumeData, ...parsedFromTextarea};
            } catch (e) {
                // If not valid JSON, store it as raw text or handle specific fields
                 currentResumeData.raw_text = resumeTextarea.value; // Example for plain text
            }
            updateLivePreview();
        });
    }

    setupTemplateSelectors();
    setupCustomizationControls();
    setupZoomControls();
    setupTooltips(); // Initialize dynamic tooltips
    setupSuggestionCardDismiss(); // For demo suggestion cards

    // Initial call for responsive adjustments
    adjustForMobile();
    window.addEventListener('resize', adjustForMobile);

    // Animate metrics if analysis section is visible on load (though it's hidden by default)
    const analysisResultsSection = document.getElementById('analysisResults');
    if (analysisResultsSection && !analysisResultsSection.classList.contains('hidden')) {
        animateMetricsOnShow();
        analysisResultsSection.dataset.metricsAnimated = "true";
    }
    console.log("Formatter script fully loaded and initialized.");
});


function handleFileUpload(e) {
    const file = e.target.files[0];
    if (file) {
        const fileName = file.name;
        const fileSize = (file.size / 1024 / 1024).toFixed(2);

        const fileInfoContainer = e.target.closest('div'); // Find parent div of input
        let fileInfoDiv = fileInfoContainer.querySelector('.file-upload-info');
        if (fileInfoDiv) fileInfoDiv.remove(); // Remove old one

        fileInfoDiv = document.createElement('div');
        fileInfoDiv.className = 'file-upload-info mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm';
        fileInfoDiv.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center"><i class="fas fa-file-alt text-blue-600 mr-2"></i>
                    <div><span class="font-medium text-gray-900">${fileName}</span><span class="text-xs text-gray-500 block">${fileSize} MB</span></div>
                </div>
                <button class="text-red-500 hover:text-red-700 remove-file-btn"><i class="fas fa-times"></i></button>
            </div>`;
        fileInfoContainer.appendChild(fileInfoDiv);

        fileInfoDiv.querySelector('.remove-file-btn').addEventListener('click', () => {
            e.target.value = ''; fileInfoDiv.remove();
        });

        // For Phase 1, let's read the file as text and put it into the resumeTextarea
        const reader = new FileReader();
        reader.onload = (event) => {
            document.getElementById('resumeText').value = event.target.result;
            // Trigger update of currentResumeData and preview
            try {
                currentResumeData = JSON.parse(event.target.result);
            } catch (err) {
                currentResumeData.raw_text = event.target.result; // Assume plain text
            }
            updateLivePreview();
        };
        reader.readAsText(file);
    }
}

function handleProcessInput() {
    // This button now primarily serves to show the demo "AI Analysis Results"
    const loadingIndicator = document.getElementById('loadingIndicator');
    const analysisResults = document.getElementById('analysisResults');

    if (loadingIndicator && analysisResults) {
        loadingIndicator.classList.remove('hidden');
        this.disabled = true;

        setTimeout(() => { // Simulate processing
            loadingIndicator.classList.add('hidden');
            analysisResults.classList.remove('hidden');
            this.disabled = false;

            const steps = document.querySelectorAll('.progress-step');
            if (steps.length > 1) { steps[1].classList.add('active'); steps[1].classList.remove('bg-gray-100'); }

            analysisResults.scrollIntoView({ behavior: 'smooth' });
            if (!analysisResults.dataset.metricsAnimated) {
                animateMetricsOnShow();
                analysisResults.dataset.metricsAnimated = "true";
            }
        }, 1500);
    }
}

async function saveResumeDataToServer() {
    const titleToSave = document.getElementById('resumeTitleInput').value || "Untitled Resume";

    // For Phase 1: content is primarily from resumeTextarea.
    // A more robust solution would build `contentToSave` from `currentResumeData`
    // which is ideally updated by various UI interactions.
    let contentToSaveStr;
    const resumeTextContent = document.getElementById('resumeText').value;
    try {
        // If resumeTextarea contains valid JSON, assume it's the desired structure.
        JSON.parse(resumeTextContent);
        contentToSaveStr = resumeTextContent;
    } catch (e) {
        // If not valid JSON, it's plain text. Wrap it.
        // Or, ideally, currentResumeData holds the structure and resumeTextContent was just one part.
        // For this phase, if currentResumeData has more than just raw_text, use it. Otherwise, wrap textarea.
        if (Object.keys(currentResumeData).length > 2 && currentResumeData.summary) { // Heuristic for structured data
             contentToSaveStr = JSON.stringify(currentResumeData);
        } else {
            contentToSaveStr = JSON.stringify({
                raw_text: resumeTextContent,
                // Include other minimal fields from currentResumeData if they were populated by default
                personal: currentResumeData.personal,
                summary: currentResumeData.summary,
                template_settings: currentResumeData.template_settings
            });
        }
    }

    const payload = {
        title: titleToSave,
        content: contentToSaveStr, // This must be a JSON string
        resume_id: globalResumeId
    };

    try {
        const response = await fetch('/resume_builder/formatter/save_resume_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', /* Add CSRF if needed */ },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (result.success) {
            if (result.resume_id && !globalResumeId) {
                globalResumeId = result.resume_id;
                // Update URL without page reload to reflect editing this new resume
                history.pushState({resumeId: globalResumeId}, "", `/resume_builder/formatter/edit/${globalResumeId}`);
            }
            showToast(result.message || 'Resume saved successfully!', 'success');
            updateLastUpdatedTimestamp();
        } else {
            showToast('Error saving resume: ' + (result.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Failed to save resume:', error);
        showToast('Failed to save resume. Check console.', 'error');
    }
}

function updateLivePreview() {
    const title = document.getElementById('resumeTitleInput')?.value || initialResumeTitle || "Untitled Resume";
    document.getElementById('previewFullName').textContent = title; // Simple mapping for now

    // Basic preview of resumeText content. A real preview would parse JSON and build HTML.
    let previewHtml = "";
    try {
        const dataForPreview = JSON.parse(document.getElementById('resumeText').value);
        // Simplistic preview: just show stringified JSON or a main field
        document.getElementById('previewSummaryText').textContent = dataForPreview.summary || JSON.stringify(dataForPreview, null, 2).substring(0, 500) + "...";
        // More detailed preview update would go here, iterating sections etc.
        // e.g., updatePreviewSection(document.getElementById('previewExperienceSection'), dataForPreview.experiences, renderExperienceItem);
    } catch (e) {
         document.getElementById('previewSummaryText').textContent = document.getElementById('resumeText').value.substring(0,500) + "...";
    }
}

// --- UI Interaction Helpers ---
function setupTemplateSelectors() {
    document.querySelectorAll('.template-card').forEach(card => {
        card.addEventListener('click', function() {
            document.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
            currentResumeData.template_settings.name = this.dataset.templateName;
            // Update progress (visual only for now)
            const steps = document.querySelectorAll('.progress-step');
            if (steps.length > 2) { steps[2].classList.add('active'); steps[2].classList.remove('bg-gray-100'); }
            // updateLivePreview(); // Full preview update would be complex
        });
    });
}

function setupCustomizationControls() {
    document.querySelectorAll('.color-picker').forEach(picker => {
        picker.addEventListener('click', function() {
            document.querySelectorAll('.color-picker').forEach(p => p.classList.remove('ring-2', 'ring-offset-2', 'ring-blue-500'));
            this.classList.add('ring-2', 'ring-offset-2', 'ring-blue-500');
            currentResumeData.template_settings.color_scheme = this.dataset.color;
            // updateLivePreview();
        });
    });
    document.querySelectorAll('.font-preview').forEach(preview => {
        preview.addEventListener('click', function() {
            document.querySelectorAll('.font-preview').forEach(p => p.classList.remove('selected'));
            this.classList.add('selected');
            currentResumeData.template_settings.font_family = this.dataset.font;
            // updateLivePreview();
        });
    });
    document.getElementById('includeContactIcons')?.addEventListener('change', function() {
        currentResumeData.template_settings.contact_icons = this.checked;
        // updateLivePreview();
    });
    document.getElementById('twoColumnLayout')?.addEventListener('change', function() {
        currentResumeData.template_settings.two_column = this.checked;
        // updateLivePreview();
    });
}

function setupZoomControls() {
    const zoomInBtn = document.getElementById('zoomInBtn');
    const zoomOutBtn = document.getElementById('zoomOutBtn');
    const zoomLevelDisplay = document.getElementById('zoomLevelDisplay');
    const previewContent = document.getElementById('resumePreviewContent');

    if (!zoomInBtn || !zoomOutBtn || !zoomLevelDisplay || !previewContent) return;

    zoomInBtn.addEventListener('click', () => {
        currentZoomLevel = Math.min(2.0, currentZoomLevel + 0.1);
        applyZoom();
    });
    zoomOutBtn.addEventListener('click', () => {
        currentZoomLevel = Math.max(0.5, currentZoomLevel - 0.1);
        applyZoom();
    });
    function applyZoom() {
        previewContent.style.transform = `scale(${currentZoomLevel})`;
        previewContent.style.transformOrigin = 'top left'; // Adjust as needed
        zoomLevelDisplay.textContent = `${Math.round(currentZoomLevel * 100)}%`;
    }
}

function setupTooltips() {
    document.body.addEventListener('mouseover', e => {
        const target = e.target.closest('.tooltip');
        if (target && target.dataset.tooltip) {
            if (document.querySelector('.tooltip-bubble')) return; // One at a time
            const tooltipBubble = document.createElement('div');
            tooltipBubble.className = 'tooltip-bubble fixed bg-gray-800 text-white px-3 py-1.5 rounded text-xs shadow-lg z-[1001] pointer-events-none'; // Ensure high z-index
            tooltipBubble.textContent = target.dataset.tooltip;
            document.body.appendChild(tooltipBubble);
            const rect = target.getBoundingClientRect();
            tooltipBubble.style.left = `${rect.left + rect.width / 2 - tooltipBubble.offsetWidth / 2}px`;
            tooltipBubble.style.top = `${rect.top - tooltipBubble.offsetHeight - 6}px`; // 6px offset
            target.addEventListener('mouseleave', () => tooltipBubble.remove(), { once: true });
            target.addEventListener('mousedown', () => tooltipBubble.remove(), { once: true });
        }
    });
}

function setupSuggestionCardDismiss() {
    // This is for the demo cards; real suggestions would be handled differently.
    document.querySelectorAll('.suggestion-card .tooltip[data-tooltip="Dismiss"]').forEach(button => {
        if(button.disabled) return; // Don't add listeners to disabled (coming soon) buttons
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const card = this.closest('.suggestion-card');
            if (card) card.remove();
            // updateSuggestionCounts(); // If counts need to be dynamic
        });
    });
}

function updateLastUpdatedTimestamp() {
    const tsElement = document.getElementById('lastUpdatedTimestamp');
    if (tsElement) {
        tsElement.textContent = `Last saved: ${new Date().toLocaleTimeString()}`;
    }
}

function showToast(message, type = 'info') {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.className = `fixed top-5 right-5 p-4 rounded-md shadow-lg text-white z-[1002]`;
    if (type === 'success') toast.classList.add('bg-green-500');
    else if (type === 'error') toast.classList.add('bg-red-500');
    else toast.classList.add('bg-blue-500');
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.transition = 'opacity 0.5s ease';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

function animateMetricsOnShow() {
    // (Same as provided, ensure it's available)
    const metrics = document.querySelectorAll('#analysisResults .metric-number');
    metrics.forEach(metric => {
        const isPercentage = metric.textContent.includes('%');
        const target = parseInt(metric.textContent.replace('%', ''));
        if (isNaN(target)) return;
        let current = 0;
        const duration = 1000; const stepTime = 50;
        const totalSteps = duration / stepTime;
        const increment = target / totalSteps;
        metric.textContent = (isPercentage ? '0%' : '0');
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                metric.textContent = target + (isPercentage ? '%' : '');
                clearInterval(timer);
            } else {
                metric.textContent = Math.floor(current) + (isPercentage ? '%' : '');
            }
        }, stepTime);
    });
}

function adjustForMobile() { /* Placeholder for any specific mobile JS adjustments */ }

// Helper for CSRF token if forms need it (Flask-WTF usually handles this in form templates)
// function getCsrfToken() {
//    return document.querySelector('input[name="csrf_token"]')?.value;
// }
