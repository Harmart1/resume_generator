// formatter.js

// --- Global State ---
let globalResumeId = null; // Set from Flask data via inline script
let currentResumeData = {}; // Main data object
let defaultResumeStructure = {
    personal: { full_name: "", job_title: "", email: "", phone: "", location: "", linkedin: "", portfolio: "" },
    summary: "",
    experiences: [], // Array of objects: {id, job_title, company, location, start_date, end_date, achievements: []}
    education: [],   // Array of objects: {id, degree, institution, field_of_study, graduation_year, gpa}
    skills: { technical_skills: [], soft_skills: [], certifications: [] }, // Arrays of strings
    additional: { projects: "", languages: "", volunteer: "" }, // Textareas for now, can be structured later
    template_settings: {
        name: "professional", color_scheme: "blue", font_family: "Inter",
        contact_icons: true, two_column: false
    }
};
let currentZoomLevel = 1.0;


// --- Utilities ---
function generateUUID() {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

function isObject(item) {
    return (item && typeof item === 'object' && !Array.isArray(item));
}

function deepMerge(target, ...sources) {
    if (!sources.length) return target;
    const source = sources.shift();
    if (isObject(target) && isObject(source)) {
        for (const key in source) {
            if (isObject(source[key])) {
                if (!target[key]) Object.assign(target, { [key]: {} });
                deepMerge(target[key], source[key]);
            } else if (Array.isArray(source[key])) {
                Object.assign(target, { [key]: source[key] });
            } else {
                Object.assign(target, { [key]: source[key] });
            }
        }
    }
    return deepMerge(target, ...sources);
}

function updateResumeTextDebugView() {
    const resumeTextarea = document.getElementById('resumeText');
    if (resumeTextarea) {
        resumeTextarea.value = JSON.stringify(currentResumeData, null, 2);
    }
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', function() {
    globalResumeId = currentResumeId;
    currentResumeData = JSON.parse(JSON.stringify(defaultResumeStructure));

    const titleInput = document.getElementById('resumeTitleInput');
    if (titleInput) {
        titleInput.value = initialResumeTitle || "Untitled Resume";
    }

    if (initialResumeContentJsonString) {
        try {
            const parsedContent = JSON.parse(initialResumeContentJsonString);
            deepMerge(currentResumeData, parsedContent);
            ['experiences', 'education'].forEach(key => {
                if (!Array.isArray(currentResumeData[key])) currentResumeData[key] = [];
                // Ensure items have IDs
                currentResumeData[key].forEach(item => { if (!item.id) item.id = generateUUID(); });
            });
            ['technical_skills', 'soft_skills', 'certifications'].forEach(key => {
                if (!Array.isArray(currentResumeData.skills[key])) currentResumeData.skills[key] = [];
            });
        } catch (e) {
            console.error("Error parsing initial resume content JSON:", e);
            currentResumeData.raw_text = initialResumeContentJsonString;
        }
    }

    populateStaticFormFields();
    renderAllDynamicSections();
    updateResumeTextDebugView(); // Populate debug view
    updateLastUpdatedTimestamp();

    setupCoreEventListeners();
    setupTemplateSelectors();
    setupCustomizationControls();

    // ***** NEW CALLS HERE *****
    applyTemplateSettingsToUI();
    updateLivePreview();         // Ensure preview reflects loaded settings immediately
    // **************************

    setupZoomControls();
    setupTooltips();
    setupSuggestionCardDismiss();

    adjustForMobile();
    window.addEventListener('resize', adjustForMobile);

    const analysisResultsSection = document.getElementById('analysisResults');
    if (analysisResultsSection && !analysisResultsSection.classList.contains('hidden')) {
        animateMetricsOnShow();
        analysisResultsSection.dataset.metricsAnimated = "true";
    }
    setupExportButtons(); // Add this call

    console.log("Formatter script initialized with dynamic editors.");
    // updateLivePreview(); // Will be enhanced later
});

// --- Export Functionality ---
function setupExportButtons() {
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    if (downloadPdfBtn) {
        downloadPdfBtn.addEventListener('click', () => {
            // Ensure the preview is fully up-to-date with any recent data changes
            // updateLivePreview(); // Called by data change handlers already

            const originalTitle = document.title;
            const resumeTitleInput = document.getElementById('resumeTitleInput');
            let resumeTitle = "resume"; // Default filename
            if (resumeTitleInput && resumeTitleInput.value) {
                resumeTitle = resumeTitleInput.value.replace(/[^a-z0-9]/gi, '_').toLowerCase();
            }
            document.title = resumeTitle; // Set for print-to-PDF filename suggestion

            window.print(); // Uses @media print styles

            // Restore original title after a short delay (print dialog might be async)
            setTimeout(() => {
                document.title = originalTitle;
            }, 1000);
        });
    }

    // Placeholder for Word export if added later
    // const downloadWordBtn = document.getElementById('downloadWordBtn');
    // if (downloadWordBtn) { /* ... */ }
}


function populateStaticFormFields() {
    // Personal Details
    document.querySelectorAll('#personalDetailsEditorContainer input.data-field, #personalDetailsEditorContainer textarea.data-field').forEach(input => {
        const path = input.dataset.path.split('.');
        let value = currentResumeData;
        path.forEach(p => value = value ? value[p] : undefined);
        if (value !== undefined) input.value = value;
    });
    // Summary
    const summaryTextarea = document.getElementById('summaryTextarea');
    if (summaryTextarea) summaryTextarea.value = currentResumeData.summary || "";
    // Additional Info
    document.querySelectorAll('#additionalInfoEditorContainer textarea.data-field').forEach(input => {
        const path = input.dataset.path.split('.');
        let value = currentResumeData;
        path.forEach(p => value = value ? value[p] : undefined);
        if (value !== undefined) input.value = value;
    });
}

function renderAllDynamicSections() {
    renderExperienceSection();
    renderEducationSection();
    renderSkillsSection();
}

function setupCoreEventListeners() {
    const titleInput = document.getElementById('resumeTitleInput');
    // Event listeners for static fields (personal, summary, additional)
    document.querySelectorAll('.data-field').forEach(input => {
        input.addEventListener('input', (e) => {
            const path = e.target.dataset.path.split('.');
            let obj = currentResumeData;
            path.forEach((p, i) => {
                if (i === path.length - 1) {
                    obj[p] = e.target.value;
                } else {
                    if (!obj[p]) obj[p] = {}; // Create intermediate objects if they don't exist
                    obj = obj[p];
                }
            });
            updateResumeTextDebugView();
            // updateLivePreview(); // Basic update for now
        });
    });

    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.addEventListener('change', handleFileUpload);
    const parseBtn = document.getElementById('parseBtn');
    if (parseBtn) parseBtn.addEventListener('click', handleProcessInput);
    const saveResumeBtn = document.getElementById('saveResumeButton');
    if (saveResumeBtn) saveResumeBtn.addEventListener('click', saveResumeDataToServer);

    if (titleInput) {
        titleInput.addEventListener('input', () => { /* updateLivePreview(); */ });
    }
    // Listener for raw JSON textarea (for debug/advanced)
    const resumeTextarea = document.getElementById('resumeText');
    if (resumeTextarea) {
        resumeTextarea.addEventListener('input', () => {
            try {
                const updatedData = JSON.parse(resumeTextarea.value);
                deepMerge(currentResumeData, updatedData);
                populateStaticFormFields(); // Reflect changes back to structured fields
                renderAllDynamicSections(); // And dynamic sections
            } catch (e) { /* Ignore parse errors while typing */ }
        });
    }
}

// --- Dynamic Section: Experience ---
function renderExperienceSection() {
    const listContainer = document.getElementById('experienceList');
    if (!listContainer) return;
    listContainer.innerHTML = ''; // Clear existing items

    currentResumeData.experiences.forEach((exp, index) => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'p-3 border border-gray-300 rounded-md space-y-2 relative';
        itemDiv.innerHTML = `
            <button class="absolute top-2 right-2 text-red-500 hover:text-red-700 delete-item-btn" data-section="experiences" data-id="${exp.id}" title="Delete Experience">&times;</button>
            <div><label class="text-xs font-medium">Job Title</label><input type="text" data-path="experiences[${index}].job_title" value="${exp.job_title || ''}" class="dynamic-field w-full p-1 border-b text-sm" placeholder="e.g., Software Engineer"></div>
            <div><label class="text-xs font-medium">Company</label><input type="text" data-path="experiences[${index}].company" value="${exp.company || ''}" class="dynamic-field w-full p-1 border-b text-sm" placeholder="e.g., Google"></div>
            <div class="grid grid-cols-2 gap-2">
                <div><label class="text-xs font-medium">Location</label><input type="text" data-path="experiences[${index}].location" value="${exp.location || ''}" class="dynamic-field w-full p-1 border-b text-sm" placeholder="e.g., Mountain View, CA"></div>
                <div><label class="text-xs font-medium">Start Date</label><input type="text" data-path="experiences[${index}].start_date" value="${exp.start_date || ''}" class="dynamic-field w-full p-1 border-b text-sm" placeholder="e.g., Jan 2020"></div>
                <div><label class="text-xs font-medium">End Date</label><input type="text" data-path="experiences[${index}].end_date" value="${exp.end_date || ''}" class="dynamic-field w-full p-1 border-b text-sm" placeholder="e.g., Present or Dec 2022"></div>
            </div>
            <div><label class="text-xs font-medium">Achievements (one per line)</label><textarea data-path="experiences[${index}].achievements" class="dynamic-field w-full p-1 border-b text-sm" rows="3" placeholder="Reduced load time by 20%...">${(exp.achievements || []).join('\n')}</textarea></div>
        `;
        listContainer.appendChild(itemDiv);
    });
    addDynamicFieldListeners(listContainer);
}

document.getElementById('addExperienceBtn')?.addEventListener('click', () => {
    const newExp = {
        id: generateUUID(), job_title: "", company: "", location: "",
        start_date: "", end_date: "", achievements: []
    };
    currentResumeData.experiences.push(newExp);
    renderExperienceSection();
    updateResumeTextDebugView();
    updateLivePreview(); // Ensure preview updates

    // Scroll to the new item and focus its first input
    const newItemElement = document.querySelector(`#experienceList .dynamic-field[data-path="experiences[${currentResumeData.experiences.length - 1}].job_title"]`);
    if (newItemElement && newItemElement.closest('.p-3')) {
        newItemElement.closest('.p-3').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        newItemElement.focus();
    }
});

// --- Dynamic Section: Education ---
function renderEducationSection() {
    const listContainer = document.getElementById('educationList');
    if (!listContainer) return;
    listContainer.innerHTML = '';
    currentResumeData.education.forEach((edu, index) => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'p-3 border border-gray-300 rounded-md space-y-2 relative';
        itemDiv.innerHTML = `
            <button class="absolute top-2 right-2 text-red-500 hover:text-red-700 delete-item-btn" data-section="education" data-id="${edu.id}" title="Delete Education Entry">&times;</button>
            <div><label class="text-xs font-medium">Degree</label><input type="text" data-path="education[${index}].degree" value="${edu.degree || ''}" class="dynamic-field w-full p-1 border-b text-sm" placeholder="e.g., B.S. Computer Science"></div>
            <div><label class="text-xs font-medium">Institution</label><input type="text" data-path="education[${index}].institution" value="${edu.institution || ''}" class="dynamic-field w-full p-1 border-b text-sm" placeholder="e.g., Stanford University"></div>
            <div class="grid grid-cols-2 gap-2">
                <div><label class="text-xs font-medium">Field of Study</label><input type="text" data-path="education[${index}].field_of_study" value="${edu.field_of_study || ''}" class="dynamic-field w-full p-1 border-b text-sm" placeholder="e.g., Artificial Intelligence"></div>
                <div><label class="text-xs font-medium">Graduation Year</label><input type="text" data-path="education[${index}].graduation_year" value="${edu.graduation_year || ''}" class="dynamic-field w-full p-1 border-b text-sm" placeholder="e.g., 2019"></div>
            </div>
            <div><label class="text-xs font-medium">GPA (Optional)</label><input type="text" data-path="education[${index}].gpa" value="${edu.gpa || ''}" class="dynamic-field w-full p-1 border-b text-sm" placeholder="e.g., 3.8/4.0"></div>
        `;
        listContainer.appendChild(itemDiv);
    });
    addDynamicFieldListeners(listContainer);
}
document.getElementById('addEducationBtn')?.addEventListener('click', () => {
    const newEdu = {
        id: generateUUID(), degree: "", institution: "", field_of_study: "", graduation_year: "", gpa: ""
    };
    currentResumeData.education.push(newEdu);
    renderEducationSection();
    updateResumeTextDebugView();
    updateLivePreview();

    const newItemElement = document.querySelector(`#educationList .dynamic-field[data-path="education[${currentResumeData.education.length - 1}].degree"]`);
    if (newItemElement && newItemElement.closest('.p-3')) {
        newItemElement.closest('.p-3').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        newItemElement.focus();
    }
});

// --- Dynamic Section: Skills ---
function renderSkillsSection() {
    const container = document.getElementById('skillsInputsContainer');
    if (!container) return;
    container.innerHTML = '';

    const skillTypes = [
        { key: 'technical_skills', label: 'Technical Skills' },
        { key: 'soft_skills', label: 'Soft Skills' },
        { key: 'certifications', label: 'Certifications' }
    ];

    skillTypes.forEach(skillType => {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'mb-4';
        sectionDiv.innerHTML = `<h4 class="text-md font-semibold text-gray-700 mb-2">${skillType.label}</h4>`;

        const tagContainer = document.createElement('div');
        tagContainer.className = 'flex flex-wrap gap-2 mb-2 skills-tag-container';
        (currentResumeData.skills[skillType.key] || []).forEach(skill => {
            const tag = document.createElement('span');
            tag.className = 'skills-tag bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm flex items-center';
            tag.innerHTML = `${skill} <button class="ml-2 text-blue-600 hover:text-blue-800 delete-skill-btn" data-skill-type="${skillType.key}" data-skill-value="${skill}">&times;</button>`;
            tagContainer.appendChild(tag);
        });
        sectionDiv.appendChild(tagContainer);

        const addSkillDiv = document.createElement('div');
        addSkillDiv.className = 'flex items-center gap-2';
        addSkillDiv.innerHTML = `
            <input type="text" class="add-skill-input flex-grow p-1 border-b text-sm" placeholder="Add ${skillType.label.slice(0,-1)}...">
            <button class="add-skill-btn bg-green-500 text-white px-3 py-1 rounded text-xs hover:bg-green-600" data-skill-type="${skillType.key}">Add</button>
        `;
        sectionDiv.appendChild(addSkillDiv);
        container.appendChild(sectionDiv);
    });
    addSkillEventListeners();
}

function addSkillEventListeners() {
    document.querySelectorAll('.add-skill-btn').forEach(button => {
        button.addEventListener('click', function() {
            const skillType = this.dataset.skillType;
            const input = this.previousElementSibling; // Assuming input is right before button
            const skillValue = input.value.trim();
            if (skillValue && !currentResumeData.skills[skillType].includes(skillValue)) {
                currentResumeData.skills[skillType].push(skillValue);
                renderSkillsSection();
                updateResumeTextDebugView();
                updateLivePreview();
            }
            input.value = '';
            input.focus(); // Focus back on the input for quick next entry
        });
    });
    document.querySelectorAll('.delete-skill-btn').forEach(button => {
        button.addEventListener('click', function() {
            const skillType = this.dataset.skillType;
            const skillValue = this.dataset.skillValue;
            currentResumeData.skills[skillType] = currentResumeData.skills[skillType].filter(s => s !== skillValue);
            renderSkillsSection();
            updateResumeTextDebugView();
        });
    });
}


// Generic handler for dynamic fields in Experience, Education
function addDynamicFieldListeners(containerElement) {
    containerElement.querySelectorAll('.dynamic-field').forEach(input => {
        input.addEventListener('input', (e) => {
            const pathString = e.target.dataset.path;
            const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;

            // Path like "experiences[0].job_title" or "experiences[0].achievements"
            const parts = pathString.match(/(\w+)\[(\d+)\]\.(\w+)/);
            if (parts) {
                const section = parts[1]; // e.g., "experiences"
                const index = parseInt(parts[2]);
                const field = parts[3]; // e.g., "job_title"

                if (currentResumeData[section] && currentResumeData[section][index]) {
                    if (field === 'achievements') { // Special handling for textarea achievements
                        currentResumeData[section][index][field] = e.target.value.split('\n').map(s => s.trim()).filter(s => s);
                    } else {
                        currentResumeData[section][index][field] = value;
                    }
                    updateResumeTextDebugView();
                    // updateLivePreview();
                }
            }
        });
    });
    containerElement.querySelectorAll('.delete-item-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const section = e.currentTarget.dataset.section; // e.g., "experiences"
            const id = e.currentTarget.dataset.id;
            currentResumeData[section] = currentResumeData[section].filter(item => item.id !== id);
            if (section === "experiences") renderExperienceSection();
            else if (section === "education") renderEducationSection();
            updateResumeTextDebugView();
            // updateLivePreview();
        });
    });
}


// --- File Upload & Processing --- (Simplified, as full parsing is complex)
function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    const fileName = file.name;
    const fileSize = (file.size / 1024 / 1024).toFixed(2);
    const fileInfoContainer = e.target.closest('div');
    let fileInfoDiv = fileInfoContainer.querySelector('.file-upload-info');
    if (fileInfoDiv) fileInfoDiv.remove();
    fileInfoDiv = document.createElement('div');
    fileInfoDiv.className = 'file-upload-info mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm';
    fileInfoDiv.innerHTML = `<div class="flex items-center justify-between">...${fileName}...</div>`; // Simplified
    fileInfoContainer.appendChild(fileInfoDiv);

    const reader = new FileReader();
    reader.onload = (event) => {
        const fileContent = event.target.result;
        document.getElementById('resumeText').value = fileContent; // Put raw content in debug view
        try {
            const parsedFromFile = JSON.parse(fileContent);
            deepMerge(currentResumeData, parsedFromFile);
            populateStaticFormFields(); // Re-populate static fields
            renderAllDynamicSections(); // Re-render dynamic sections
            updateResumeTextDebugView();
        } catch (err) {
            console.warn("Uploaded file content is not valid JSON. Displaying in Raw JSON view.");
            currentResumeData = JSON.parse(JSON.stringify(defaultResumeStructure)); // Reset to default
            currentResumeData.raw_text = fileContent; // Store raw text
            populateStaticFormFields();
            renderAllDynamicSections(); // Render empty sections
            updateResumeTextDebugView(); // Show raw_text in debug
        }
        // updateLivePreview();
    };
    reader.readAsText(file);
}

function handleProcessInput() { // Demo functionality
    const loadingIndicator = document.getElementById('loadingIndicator');
    const analysisResults = document.getElementById('analysisResults');
    if (loadingIndicator && analysisResults) {
        loadingIndicator.classList.remove('hidden');
        document.getElementById('parseBtn').disabled = true;
        setTimeout(() => {
            loadingIndicator.classList.add('hidden');
            analysisResults.classList.remove('hidden');
            document.getElementById('parseBtn').disabled = false;
            const steps = document.querySelectorAll('.progress-step');
            if (steps.length > 1) { steps[1].classList.add('active'); steps[1].classList.remove('bg-gray-100'); }
            analysisResults.scrollIntoView({ behavior: 'smooth' });
            if (!analysisResults.dataset.metricsAnimated) animateMetricsOnShow();
        }, 1500);
    }
}

// --- Save Data ---
async function saveResumeDataToServer() {
    const saveButton = document.getElementById('saveResumeButton');
    const originalButtonHTML = saveButton.innerHTML; // Store full HTML content
    saveButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';
    saveButton.disabled = true;

    const titleToSave = document.getElementById('resumeTitleInput').value || "Untitled Resume";

    // Ensure currentResumeData is up-to-date if user edited JSON directly in textarea
    // This was part of previous logic, ensure it's still relevant or simplified
    // if structured forms are the sole source of truth for currentResumeData.
    const resumeTextarea = document.getElementById('resumeText');
    if (resumeTextarea) {
        try {
            const dataFromTextarea = JSON.parse(resumeTextarea.value);
            // Only merge if the debug view actually differs, to avoid overwriting structured changes
            if (JSON.stringify(dataFromTextarea) !== JSON.stringify(currentResumeData)) {
                 deepMerge(currentResumeData, dataFromTextarea);
                 // If debug view was edited, re-render forms to reflect this merge
                 populateStaticFormFields();
                 renderAllDynamicSections();
                 console.log("Data merged from Raw JSON view before saving.");
            }
        } catch (e) {
            // Ignore if not valid JSON, currentResumeData from forms is primary
        }
    }

    // Clean up raw_text if structured data is present
    if (currentResumeData.summary || (currentResumeData.experiences && currentResumeData.experiences.length > 0)) {
        delete currentResumeData.raw_text;
    }

    const contentToSaveStr = JSON.stringify(currentResumeData);
    const payload = { title: titleToSave, content: contentToSaveStr, resume_id: globalResumeId };

    try {
        const response = await fetch('/resume_builder/formatter/save_resume_data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (result.success) {
            if (result.resume_id && (globalResumeId === null || globalResumeId === undefined)) {
                globalResumeId = result.resume_id;
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
    } finally {
        saveButton.innerHTML = originalButtonHTML; // Restore original HTML
        saveButton.disabled = false;
    }
}


// --- Live Preview ---
function updateLivePreview() {
    const previewEl = document.getElementById('resumePreviewContent');
    if (!previewEl) return;

    // Apply Template Name Class
    const templateName = currentResumeData.template_settings.name || 'professional';
    previewEl.className = 'resume-preview'; // Reset classes
    previewEl.classList.add(`template-${templateName}`);

    // Apply Color Scheme (using CSS Variables)
    const colorMap = {
        blue: '#2563EB', purple: '#7C3AED', green: '#10B981',
        red: '#EF4444', yellow: '#F59E0B', gray: '#4B5563'
    };
    const accentColor = colorMap[currentResumeData.template_settings.color_scheme] || colorMap.blue;
    previewEl.style.setProperty('--preview-accent-color', accentColor);
    // Example: Section title borders might use this variable in formatter.css
    // .template-professional .section-title-border { border-color: var(--preview-accent-color); }
    // For direct application to example elements:
    previewEl.querySelectorAll('.border-blue-600').forEach(el => el.style.borderColor = accentColor);


    // Apply Font Family
    const fontFamily = currentResumeData.template_settings.font_family || 'Inter';
    previewEl.style.fontFamily = `'${fontFamily}', sans-serif`;

    // Apply Boolean Settings
    if (currentResumeData.template_settings.two_column) {
        previewEl.classList.add('layout-two-column');
    } else {
        previewEl.classList.remove('layout-two-column');
    }
    // Contact icons are handled during contact info rendering based on template_settings.contact_icons

    // Render content
    const personal = currentResumeData.personal || {};
    const summary = currentResumeData.summary || "";
    const experiences = currentResumeData.experiences || [];
    const educationItems = currentResumeData.education || [];
    const skills = currentResumeData.skills || {};
    // const additional = currentResumeData.additional || {}; // For later

    // Personal Info
    document.getElementById('previewFullName').textContent = personal.full_name || "Your Name";
    document.getElementById('previewJobTitle').textContent = personal.job_title || "Your Job Title";

    const contactInfoEl = document.getElementById('previewContactInfo');
    contactInfoEl.innerHTML = ''; // Clear old
    const showIcons = currentResumeData.template_settings.contact_icons;
    if (personal.email) contactInfoEl.innerHTML += `<span>${showIcons ? '<i class="fas fa-envelope mr-1"></i>':''} ${personal.email}</span>`;
    if (personal.phone) contactInfoEl.innerHTML += `<span class="ml-3">${showIcons ? '<i class="fas fa-phone mr-1"></i>':''} ${personal.phone}</span>`;
    if (personal.location) contactInfoEl.innerHTML += `<span class="ml-3">${showIcons ? '<i class="fas fa-map-marker-alt mr-1"></i>':''} ${personal.location}</span>`;
    if (personal.linkedin) contactInfoEl.innerHTML += `<span class="ml-3"><a href="${personal.linkedin}" target="_blank" class="text-blue-600 hover:underline">${showIcons ? '<i class="fab fa-linkedin mr-1"></i>':''}LinkedIn</a></span>`;
    if (personal.portfolio) contactInfoEl.innerHTML += `<span class="ml-3"><a href="${personal.portfolio}" target="_blank" class="text-blue-600 hover:underline">${showIcons ? '<i class="fas fa-globe mr-1"></i>':''}Portfolio</a></span>`;

    // Summary
    document.getElementById('previewSummaryText').textContent = summary;
    document.getElementById('previewSummarySection').style.display = summary ? 'block' : 'none';

    // Experience
    const expSectionEl = document.getElementById('previewExperienceSection');
    expSectionEl.innerHTML = `<h2 class="text-lg font-semibold text-gray-900 mb-3 border-b-2 pb-1 preview-section-title">EXPERIENCE</h2>`;
    if (experiences.length > 0) {
        experiences.forEach(exp => {
            const expDiv = document.createElement('div');
            expDiv.className = 'mb-4';
            let achievementsHTML = '';
            if (exp.achievements && exp.achievements.length > 0) {
                achievementsHTML = '<ul class="list-disc list-inside text-sm text-gray-700 space-y-1 mt-1">';
                exp.achievements.forEach(ach => achievementsHTML += `<li>${ach}</li>`);
                achievementsHTML += '</ul>';
            }
            expDiv.innerHTML = `
                <div class="flex justify-between items-start mb-1">
                    <div>
                        <h3 class="font-semibold text-gray-900">${exp.job_title || 'Job Title'}</h3>
                        <p class="text-sm text-gray-700">${exp.company || 'Company'}${exp.location ? `, ${exp.location}` : ''}</p>
                    </div>
                    <span class="text-sm text-gray-600 whitespace-nowrap">${exp.start_date || 'StartDate'} - ${exp.end_date || 'EndDate'}</span>
                </div>
                ${achievementsHTML}
            `;
            expSectionEl.appendChild(expDiv);
        });
        expSectionEl.style.display = 'block';
    } else {
        expSectionEl.style.display = 'none';
    }

    // Education
    const eduSectionEl = document.getElementById('previewEducationSection');
    eduSectionEl.innerHTML = `<h2 class="text-lg font-semibold text-gray-900 mb-3 border-b-2 pb-1 preview-section-title">EDUCATION</h2>`;
    if (educationItems.length > 0) {
        educationItems.forEach(edu => {
            const eduDiv = document.createElement('div');
            eduDiv.className = 'mb-3';
            eduDiv.innerHTML = `
                <div class="flex justify-between items-start">
                    <div>
                        <h3 class="font-semibold text-gray-900">${edu.degree || 'Degree'}</h3>
                        <p class="text-sm text-gray-700">${edu.institution || 'Institution'}</p>
                        ${edu.field_of_study ? `<p class="text-xs text-gray-600">${edu.field_of_study}</p>` : ''}
                    </div>
                    <span class="text-sm text-gray-600 whitespace-nowrap">${edu.graduation_year || 'Year'}</span>
                </div>
                ${edu.gpa ? `<p class="text-xs text-gray-500">GPA: ${edu.gpa}</p>` : ''}
            `;
            eduSectionEl.appendChild(eduDiv);
        });
        eduSectionEl.style.display = 'block';
    } else {
        eduSectionEl.style.display = 'none';
    }

    // Skills
    const skillsSectionEl = document.getElementById('previewSkillsSection');
    skillsSectionEl.innerHTML = `<h2 class="text-lg font-semibold text-gray-900 mb-3 border-b-2 pb-1 preview-section-title">SKILLS</h2>`;
    let hasSkills = false;
    const skillsContentDiv = document.createElement('div');
    // For two-column layout, skills might need different styling
    skillsContentDiv.className = currentResumeData.template_settings.two_column ? 'space-y-1' : 'flex flex-wrap gap-2';

    const renderSkillCategory = (category, label) => {
        if (skills[category] && skills[category].length > 0) {
            hasSkills = true;
            if (currentResumeData.template_settings.two_column) { // Different rendering for two-column
                 skillsContentDiv.innerHTML += `<div class="mb-1"><strong class="text-sm">${label}:</strong> ${skills[category].join(', ')}</div>`;
            } else {
                skills[category].forEach(skill => {
                    const skillTag = document.createElement('span');
                    skillTag.style.backgroundColor = `color-mix(in srgb, var(--preview-accent-color) 20%, white)`; // Lighter accent
                    skillTag.style.color = `color-mix(in srgb, var(--preview-accent-color) 100%, black)`; // Darker accent text
                    skillTag.className = 'px-2 py-1 rounded text-sm'; // Removed bg-blue-100 text-blue-800
                    skillTag.textContent = skill;
                    skillsContentDiv.appendChild(skillTag);
                });
            }
        }
    };
    renderSkillCategory('technical_skills', 'Technical');
    renderSkillCategory('soft_skills', 'Soft');
    renderSkillCategory('certifications', 'Certifications');


    if(hasSkills) {
        skillsSectionEl.appendChild(skillsContentDiv);
        skillsSectionEl.style.display = 'block';
    } else {
        skillsSectionEl.style.display = 'none';
    }
    console.log("Live preview updated.");
}


// --- UI Interaction Helpers ---
function setupTemplateSelectors() {
    document.querySelectorAll('.template-card').forEach(card => {
        card.addEventListener('click', function() {
            document.querySelectorAll('.template-card').forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
            currentResumeData.template_settings.name = this.dataset.templateName;
            const steps = document.querySelectorAll('.progress-step');
            if (steps.length > 2) { steps[2].classList.add('active'); steps[2].classList.remove('bg-gray-100'); }
            updateLivePreview();
        });
    });
}

function setupCustomizationControls() {
    document.querySelectorAll('.color-picker').forEach(picker => {
        picker.addEventListener('click', function() {
            document.querySelectorAll('.color-picker').forEach(p => p.classList.remove('ring-2', 'ring-offset-2', 'ring-blue-500')); // TODO: use actual color for ring
            this.classList.add('ring-2', 'ring-offset-2', 'ring-blue-500'); // Example, should reflect chosen color
            currentResumeData.template_settings.color_scheme = this.dataset.color;
            updateLivePreview();
        });
    });
    document.querySelectorAll('.font-preview').forEach(preview => {
        preview.addEventListener('click', function() {
            document.querySelectorAll('.font-preview').forEach(p => p.classList.remove('selected'));
            this.classList.add('selected');
            currentResumeData.template_settings.font_family = this.dataset.font;
            updateLivePreview();
        });
    });
    document.getElementById('includeContactIcons')?.addEventListener('change', function() {
        currentResumeData.template_settings.contact_icons = this.checked;
        updateLivePreview();
    });
    document.getElementById('twoColumnLayout')?.addEventListener('change', function() {
        currentResumeData.template_settings.two_column = this.checked;
        updateLivePreview();
    });
}

function setupZoomControls() {
    // ... (same as before)
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
        previewContent.style.transformOrigin = 'top left';
        zoomLevelDisplay.textContent = `${Math.round(currentZoomLevel * 100)}%`;
    }
}

function setupTooltips() {
    // ... (same as before)
    document.body.addEventListener('mouseover', e => {
        const target = e.target.closest('.tooltip');
        if (target && target.dataset.tooltip) {
            if (document.querySelector('.tooltip-bubble')) return;
            const tooltipBubble = document.createElement('div');
            tooltipBubble.className = 'tooltip-bubble fixed bg-gray-800 text-white px-3 py-1.5 rounded text-xs shadow-lg z-[1001] pointer-events-none';
            tooltipBubble.textContent = target.dataset.tooltip;
            document.body.appendChild(tooltipBubble);
            const rect = target.getBoundingClientRect();
            tooltipBubble.style.left = `${rect.left + rect.width / 2 - tooltipBubble.offsetWidth / 2}px`;
            tooltipBubble.style.top = `${rect.top - tooltipBubble.offsetHeight - 6}px`;
            target.addEventListener('mouseleave', () => tooltipBubble.remove(), { once: true });
            target.addEventListener('mousedown', () => tooltipBubble.remove(), { once: true });
        }
    });
}

function setupSuggestionCardDismiss() {
    document.querySelectorAll('.suggestion-dismiss-btn').forEach(button => {
        if(button.disabled) return;
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const card = this.closest('.suggestion-card');
            if (card) {
                card.remove(); // Remove the card from the DOM
                updateSuggestionCounts(); // Update counts after dismissing
            }
        });
    });
}

function setupAISuggestionApplyButtons() {
    document.querySelectorAll('.apply-suggestion-btn').forEach(button => {
        if (button.disabled) return;

        button.addEventListener('click', function() {
            const suggestionType = this.dataset.suggestionType;
            const card = this.closest('.suggestion-card');
            let success = false;
            let affectedSectionToRender = null; // To specify which editor section might need re-rendering

            if (suggestionType === 'quantifyAchievements') {
                if (currentResumeData.experiences && currentResumeData.experiences.length > 0) {
                    const firstExp = currentResumeData.experiences[0];
                    if (!firstExp.achievements) firstExp.achievements = [];
                    // Add to the beginning for visibility
                    firstExp.achievements.unshift("Simulated: Increased key metric by 25% through strategic initiative.");
                    success = true;
                    affectedSectionToRender = renderExperienceSection;
                } else {
                    showToast("Please add an experience item first to apply this suggestion.", "info");
                }
            } else if (suggestionType === 'actionVerbs') {
                if (currentResumeData.summary) {
                    currentResumeData.summary = currentResumeData.summary.replace(/Helped with/gi, "Facilitated")
                                                                     .replace(/Managed/gi, "Spearheaded")
                                                                     .replace(/Responsible for/gi, "Pioneered");
                    if (!currentResumeData.summary.includes("Facilitated") && !currentResumeData.summary.includes("Spearheaded") && !currentResumeData.summary.includes("Pioneered")) {
                        currentResumeData.summary = "Simulated: Spearheaded new initiative for summary. " + currentResumeData.summary; // Ensure a change if no common verbs found
                    }
                    success = true;
                    affectedSectionToRender = () => { // Re-populate summary textarea
                        const summaryTextarea = document.getElementById('summaryTextarea');
                        if (summaryTextarea) summaryTextarea.value = currentResumeData.summary || "";
                    };
                } else if (currentResumeData.experiences && currentResumeData.experiences.length > 0 && currentResumeData.experiences[0].achievements && currentResumeData.experiences[0].achievements.length > 0) {
                    let firstAchievement = currentResumeData.experiences[0].achievements[0];
                    let originalAchievement = firstAchievement;
                    firstAchievement = firstAchievement.replace(/Helped with/gi, "Facilitated")
                                                       .replace(/Managed/gi, "Spearheaded")
                                                       .replace(/Responsible for/gi, "Pioneered");
                    if (firstAchievement === originalAchievement) { // If no common weak verbs found, prepend a simulated change
                        firstAchievement = "Simulated: Spearheaded " + firstAchievement;
                    }
                    currentResumeData.experiences[0].achievements[0] = firstAchievement;
                    success = true;
                    affectedSectionToRender = renderExperienceSection;
                } else {
                     showToast("Please add a summary or an experience item to apply this suggestion.", "info");
                }
            }

            if (success) {
                card.classList.remove('pending');
                card.classList.add('applied');
                const badge = card.querySelector('.suggestion-impact-badge');
                if (badge) {
                    badge.classList.remove('bg-yellow-100', 'text-yellow-800', 'bg-blue-100', 'text-blue-800');
                    badge.classList.add('bg-green-100', 'text-green-800');
                    badge.textContent = 'Applied';
                }
                this.innerHTML = '<i class="fas fa-undo mr-1"></i>Undo';
                this.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                this.classList.add('bg-gray-400', 'hover:bg-gray-500', 'opacity-70', 'cursor-not-allowed');
                this.disabled = true; // For Phase 3, Undo is non-functional, so disable after apply.

                if (affectedSectionToRender) affectedSectionToRender();
                updateLivePreview();
                updateResumeTextDebugView();
                updateSuggestionCounts();
                showToast("Suggestion applied (simulated).", "success");
            }
        });
    });
}


function updateSuggestionCounts() {
    const appliedCountEl = document.getElementById('appliedCount');
    const totalActiveSuggestionsEl = document.getElementById('totalActiveSuggestions'); // Span for the number of active suggestions
    const suggestionsList = document.getElementById('suggestionsList');
    const pendingCountHeaderEl = document.getElementById('pendingSuggestionsCount'); // Span next to section title

    if (!appliedCountEl || !totalActiveSuggestionsEl || !suggestionsList || !pendingCountHeaderEl) return;

    let totalInteractiveInList = 0;
    let appliedInList = 0;
    let pendingInteractiveInList = 0;

    suggestionsList.querySelectorAll('.suggestion-card').forEach(card => {
        const applyBtn = card.querySelector('.apply-suggestion-btn');
        // A card is considered interactive if its apply button has a suggestion type (i.e., it's not just a placeholder)
        if (applyBtn && applyBtn.dataset.suggestionType) {
            totalInteractiveInList++;
            if (card.classList.contains('applied')) {
                appliedInList++;
            } else if (card.classList.contains('pending') && !applyBtn.disabled) {
                // Count as pending only if its apply button is not disabled (meaning it's one of the active ones)
                pendingInteractiveInList++;
            }
        }
    });

    appliedCountEl.textContent = appliedInList;
    totalActiveSuggestionsEl.textContent = totalInteractiveInList;

    pendingCountHeaderEl.textContent = `(${pendingInteractiveInList} interactive pending)`;
}


function updateLastUpdatedTimestamp() {
    // ... (same as before)
    const tsElement = document.getElementById('lastUpdatedTimestamp');
    if (tsElement) {
        tsElement.textContent = `Last saved: ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
}

function showToast(message, type = 'info') {
    // ... (same as before)
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
    // ... (same as before)
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

// --- UI State Sync for Template Settings ---
function applyTemplateSettingsToUI() {
    const settings = currentResumeData.template_settings;

    // Template Card
    document.querySelectorAll('.template-card').forEach(card => {
        if (card.dataset.templateName === settings.name) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });

    // Color Picker
    document.querySelectorAll('.color-picker').forEach(picker => {
        picker.classList.remove('ring-2', 'ring-offset-2', 'ring-blue-500'); // Reset all
        if (picker.dataset.color === settings.color_scheme) {
            picker.classList.add('ring-2', 'ring-offset-2', 'ring-blue-500'); // Active state
        }
    });

    // Font Preview
    document.querySelectorAll('.font-preview').forEach(preview => {
        if (preview.dataset.font === settings.font_family) {
            preview.classList.add('selected');
        } else {
            preview.classList.remove('selected');
        }
    });

    // Checkboxes
    const contactIconsCheckbox = document.getElementById('includeContactIcons');
    if (contactIconsCheckbox) {
        contactIconsCheckbox.checked = settings.contact_icons;
    }
    const twoColumnCheckbox = document.getElementById('twoColumnLayout');
    if (twoColumnCheckbox) {
        twoColumnCheckbox.checked = settings.two_column;
    }

    console.log("Template settings applied to UI controls based on currentResumeData.");
}

function adjustForMobile() { /* Placeholder */ }
