document.addEventListener("DOMContentLoaded", () => {
    let currentUserTier = "free"; // Default user tier
    let lastResumeAnalysisData = null; // To store keywords and entities from resume analysis
    const userTierSelector = document.getElementById('userTierSelector');
    const subscriptionStatusDisplay = document.getElementById('subscriptionStatus');
    const subscribeButton = document.getElementById('subscribeButton');

    function updateUserTierUI(tier) {
        currentUserTier = tier;
        userTierSelector.value = tier;
        if (tier === "premium") {
            subscriptionStatusDisplay.textContent = "Status: Premium Subscriber";
            subscribeButton.textContent = "You are Subscribed to Premium";
            subscribeButton.disabled = true;
        } else {
            subscriptionStatusDisplay.textContent = "Status: Free Tier";
            subscribeButton.textContent = "Subscribe to Premium";
            subscribeButton.disabled = false;
        }
        console.log(`User tier set to: ${currentUserTier}`);
    }

    if (userTierSelector) {
        userTierSelector.addEventListener('change', (event) => {
            updateUserTierUI(event.target.value);
        });
    }

    if (subscribeButton) {
        subscribeButton.addEventListener('click', () => {
            if (currentUserTier === "free") {
                updateUserTierUI("premium");
                // In a real app, this would involve a payment flow.
                // For now, just update the UI and tier.
                alert("Congratulations! You are now a Premium Subscriber and have access to all features.");
            }
        });
    }

    // Initialize UI based on default tier
    if(userTierSelector && subscriptionStatusDisplay && subscribeButton){
        updateUserTierUI(currentUserTier);
    }


    const analyzeButton = document.getElementById('analyzeButton');
    const resumeUploadInput = document.getElementById('resumeUpload'); // Note: Task mentions resumeUploadInput, ensure this ID is correct in HTML if used.
    const resultsDisplay = document.getElementById('results-display');
    const resumeTextInput = document.getElementById('resumeTextInput');
    const analyzeTextButton = document.getElementById('analyzeTextButton');
    const dropZone = document.querySelector('.upload-section'); // Target the whole upload section as the drop zone

    // Common function to perform resume analysis (used by both file upload and text input)
    async function performResumeAnalysis(payload, isJsonPayload, buttonElement, originalButtonText, loadingText) {
        buttonElement.disabled = true;
        buttonElement.textContent = loadingText;
        resultsDisplay.innerHTML = ''; // Clear previous results
        resultsDisplay.style.color = '#333'; // Default text color for messages

        try {
            const fetchOptions = {
                method: 'POST',
                body: isJsonPayload ? JSON.stringify(payload) : payload,
            };
            if (isJsonPayload) {
                fetchOptions.headers = { 'Content-Type': 'application/json' };
            }

            const response = await fetch('/analyze_resume', fetchOptions);

            if (response.ok) {
                const data = await response.json();
                let resultsHTML = `<h3>Resume Analysis for ${data.filename}</h3>`;
                resultsHTML += `<p><strong>Message:</strong> ${data.message}</p>`;

                if (data.keywords && data.keywords.length > 0) {
                    resultsHTML += `<h4>Keywords</h4><ul>`;
                    data.keywords.forEach(kw => {
                        resultsHTML += `<li><strong>${kw.text}</strong> (Relevance: ${kw.relevance ? kw.relevance.toFixed(2) : 'N/A'})</li>`;
                    });
                    resultsHTML += `</ul>`;
                } else {
                    resultsHTML += `<p>No keywords extracted.</p>`;
                }

                if (data.entities && data.entities.length > 0) {
                    resultsHTML += `<h4>Entities</h4><ul>`;
                    data.entities.forEach(entity => {
                        resultsHTML += `<li><strong>${entity.type}:</strong> ${entity.text} (Relevance: ${entity.relevance ? entity.relevance.toFixed(2) : 'N/A'})</li>`;
                    });
                    resultsHTML += `</ul>`;
                } else {
                    resultsHTML += `<p>No entities extracted.</p>`;
                }

                resultsDisplay.innerHTML = resultsHTML;
                resultsDisplay.style.color = 'initial';

                lastResumeAnalysisData = {
                    keywords: data.keywords || [],
                    entities: data.entities || []
                };
                console.log("Stored resume analysis data:", lastResumeAnalysisData);
            } else {
                lastResumeAnalysisData = null;
                let errorMessage = `Error: ${response.status} ${response.statusText}`;
                try {
                    const errorData = await response.json();
                    if (errorData && errorData.error) {
                        errorMessage = errorData.error;
                    }
                } catch (e) {
                    console.error("Failed to parse error JSON for /analyze_resume:", e);
                }
                resultsDisplay.innerHTML = `<p class="error-message">${errorMessage}</p>`;
            }
        } catch (error) {
            console.error('Fetch error for /analyze_resume:', error);
            resultsDisplay.innerHTML = `<p class="error-message">A network error occurred, or the server is unreachable. Please try again later.</p>`;
        } finally {
            buttonElement.disabled = false;
            buttonElement.textContent = originalButtonText;
        }
    }

    if (analyzeButton) {
        analyzeButton.addEventListener('click', async () => {
            const originalButtonText = analyzeButton.textContent;

            if (!resumeUploadInput || !resumeUploadInput.files || resumeUploadInput.files.length === 0) {
                resultsDisplay.innerHTML = '<p class="error-message">Please select a resume file first.</p>';
                return;
            }
            const file = resumeUploadInput.files[0];
            const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
            if (!allowedTypes.includes(file.type)) {
                resultsDisplay.innerHTML = '<p class="error-message">Invalid file type. Please upload a PDF, DOC, DOCX, or TXT file.</p>';
                return;
            }
            const formData = new FormData();
            formData.append('resume', file);

            performResumeAnalysis(formData, false, analyzeButton, originalButtonText, 'Analyzing...');
        });
    }

    // Drag and Drop Functionality for Resume Analysis
    if (dropZone) {
        dropZone.addEventListener('dragover', (event) => {
            event.preventDefault(); // Necessary to allow dropping
            dropZone.classList.add('drop-zone-active');
        });

        dropZone.addEventListener('dragleave', (event) => {
            dropZone.classList.remove('drop-zone-active');
        });

        dropZone.addEventListener('drop', async (event) => {
            event.preventDefault(); // Prevent default browser action (opening file)
            dropZone.classList.remove('drop-zone-active');

            const files = event.dataTransfer.files;

            if (files.length === 0) {
                resultsDisplay.innerHTML = '<p class="error-message">No files dropped.</p>';
                return;
            }
            if (files.length > 1) {
                resultsDisplay.innerHTML = '<p class="error-message">Please drop only one file at a time.</p>';
                return;
            }

            const file = files[0];

            // Basic client-side file type validation (optional, backend also validates)
            const allowedExtensions = ['.pdf', '.docx', '.txt'];
            const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
            if (!allowedExtensions.includes(fileExtension)) {
                 resultsDisplay.innerHTML = `<p class="error-message">Invalid file type: ${file.name}. Please upload .txt, .pdf, or .docx.</p>`;
                 return;
            }

            const originalButtonText = analyzeButton.textContent; // Use analyzeButton's text for consistency

            const formData = new FormData();
            formData.append('resume', file);

            // Call the existing common analysis function
            // Pass analyzeButton itself, its original text, and a specific loading message for dropped files
            await performResumeAnalysis(formData, false, analyzeButton, originalButtonText, 'Analyzing Dropped File...');
        });
    }

    if (analyzeTextButton) {
        analyzeTextButton.addEventListener('click', async () => {
            const originalButtonText = analyzeTextButton.textContent;
            const resumeText = resumeTextInput.value.trim();

            if (!resumeText) {
                resultsDisplay.innerHTML = '<p class="error-message">Please paste some resume text to analyze.</p>';
                return;
            }

            const jsonData = { resume_text: resumeText, filename: "pasted_resume.txt" };
            performResumeAnalysis(jsonData, true, analyzeTextButton, originalButtonText, 'Analyzing Text...');
        });
    }

    // New: Job Market Insights (AI Jules) Feature Logic
    const getJobMarketInsightsButton = document.getElementById('getJobMarketInsightsButton');
    const jobMarketInsightsDisplay = document.getElementById('jobMarketInsightsDisplay');

    if (getJobMarketInsightsButton) {
        getJobMarketInsightsButton.addEventListener('click', async () => {
            const originalButtonText = getJobMarketInsightsButton.textContent;
            getJobMarketInsightsButton.disabled = true;
            getJobMarketInsightsButton.textContent = 'Fetching Insights...';
            jobMarketInsightsDisplay.innerHTML = ''; // Clear previous

            if (!lastResumeAnalysisData || !lastResumeAnalysisData.keywords || !lastResumeAnalysisData.entities) {
                jobMarketInsightsDisplay.textContent = 'Please analyze your resume first to get keywords and entities for job market insights.';
                jobMarketInsightsDisplay.style.color = 'red';
                // Restore button state even on early validation failure
                getJobMarketInsightsButton.disabled = false;
                getJobMarketInsightsButton.textContent = originalButtonText;
                return;
            }

            // jobMarketInsightsDisplay.textContent = 'Fetching job market insights...'; // Handled by button
            jobMarketInsightsDisplay.style.color = '#333'; // Default text color for messages

            try {
                const payload = {
                    resume_keywords: lastResumeAnalysisData.keywords,
                    resume_entities: lastResumeAnalysisData.entities,
                    user_tier: currentUserTier // Send user tier
                };

                const response = await fetch('/get_job_market_insights', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload),
                });

                if (response.ok) {
                    const data = await response.json();
                    let resultsHTML = `<h4>Job Market Insights (General Guidance)</h4>`; // Changed heading
                    resultsHTML += `<p><strong>Message:</strong> ${data.message}</p>`;

                    if (data.identified_skills_for_insights && data.identified_skills_for_insights.length > 0) {
                        resultsHTML += `<p><strong>Based on skills:</strong> ${data.identified_skills_for_insights.join(', ')}</p>`;
                    }

                    resultsHTML += `<p><strong>Insights:</strong></p>`; // Changed from H4 to P
                    if (data.insights_text) {
                        // Replace newlines with <br> for paragraph-like display.
                        // If Gemini returns actual list markdown, more sophisticated parsing might be needed.
                        resultsHTML += `<div style="text-align: left; padding: 5px;">${data.insights_text.replace(/\n/g, '<br>')}</div>`;
                    } else {
                        resultsHTML += `<p>No specific insights generated at this time.</p>`;
                    }

                    // Preserve the disclaimer (assuming it's correctly styled/positioned already if it was part of a previous step)
                    // For this subtask, we ensure it's programmatically added if not already managed by a static part of HTML.
                    // If the disclaimer was part of the original `data.insights_text` or `data.message`, this is fine.
                    // If it needs to be a separate, static element, it should be outside this dynamic HTML generation.
                    // The prompt mentioned a "disclaimer-message" class, so let's assume it's part of the data or added after this block.
                    // For now, adding it here as per task description structure:
                    resultsHTML += `<p class="disclaimer-message" style="font-size: 0.9em; color: #555; margin-top:15px;">Note: These insights are AI-generated based on general knowledge and are not real-time job market data. They are intended for informational purposes only.</p>`;

                    jobMarketInsightsDisplay.innerHTML = resultsHTML;
                    jobMarketInsightsDisplay.style.color = '#0077b6';
                } else {
                    let errorMessage = `Error: ${response.status} ${response.statusText}`;
                    try {
                        const errorData = await response.json();
                        if (errorData && errorData.error) {
                            errorMessage = errorData.error;
                        }
                    } catch (e) {
                        console.error("Failed to parse error JSON for get_job_market_insights:", e);
                    }
                    jobMarketInsightsDisplay.innerHTML = `<p class="error-message">${errorMessage}</p>`;
                }
            } catch (error) {
                console.error('Fetch error for get_job_market_insights:', error);
                jobMarketInsightsDisplay.innerHTML = `<p class="error-message">A network error occurred, or the server is unreachable. Please try again later.</p>`;
            } finally {
                getJobMarketInsightsButton.disabled = false;
                getJobMarketInsightsButton.textContent = originalButtonText;
            }
        });
    }

    // New: Smart Suggestions (AI Jules) Feature Logic
    const getSmartSuggestionsButton = document.getElementById('getSmartSuggestionsButton');
    const smartSuggestionsDisplay = document.getElementById('smartSuggestionsDisplay');
    // Re-use resumeUploadInput from the Resume Analyzer section for file access

    if (getSmartSuggestionsButton) {
        getSmartSuggestionsButton.addEventListener('click', async () => {
            const originalButtonText = getSmartSuggestionsButton.textContent;
            getSmartSuggestionsButton.disabled = true;
            getSmartSuggestionsButton.textContent = 'Generating...';
            smartSuggestionsDisplay.innerHTML = ''; // Clear previous

            if (!resumeUploadInput || !resumeUploadInput.files || resumeUploadInput.files.length === 0) {
                smartSuggestionsDisplay.textContent = 'Please upload a resume first using the "Upload Your Resume" section.';
                smartSuggestionsDisplay.style.color = 'red';
                getSmartSuggestionsButton.disabled = false;
                getSmartSuggestionsButton.textContent = originalButtonText;
                return;
            }

            const file = resumeUploadInput.files[0];
            const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
            if (!allowedTypes.includes(file.type)) {
                smartSuggestionsDisplay.textContent = 'Invalid file type for Smart Suggestions. Please upload a PDF, DOC, DOCX, or TXT file.';
                smartSuggestionsDisplay.style.color = 'red';
                getSmartSuggestionsButton.disabled = false;
                getSmartSuggestionsButton.textContent = originalButtonText;
                return;
            }

            const formData = new FormData();
            formData.append('resume', file);
            formData.append('user_tier', currentUserTier); // Add user tier

            // smartSuggestionsDisplay.textContent = 'Generating smart suggestions...'; // Handled by button
            smartSuggestionsDisplay.style.color = '#333'; // Default text color for messages

            try {
                const response = await fetch('/get_smart_suggestions', {
                    method: 'POST',
                    body: formData,
                });

                if (response.ok) {
                    const data = await response.json();
                    let resultsHTML = `<h4>Smart Suggestions:</h4>`; // Added heading
                    resultsHTML += `<p><strong>${data.message}</strong></p>`; // Wrap message in <p>
                    if (data.suggestions && data.suggestions.length > 0) {
                        resultsHTML += `<ol>`; // Using ordered list
                        data.suggestions.forEach(suggestion => {
                            resultsHTML += `<li>${suggestion}</li>`;
                        });
                        resultsHTML += `</ol>`;
                    } else {
                        resultsHTML += `<p>No specific suggestions available at this time.</p>`;
                    }
                    smartSuggestionsDisplay.innerHTML = resultsHTML;
                    smartSuggestionsDisplay.style.color = '#5a0099'; // A distinct purple color
                } else {
                    let errorMessage = `Error: ${response.status} ${response.statusText}`;
                    try {
                        const errorData = await response.json();
                        if (errorData && errorData.error) {
                            errorMessage = errorData.error;
                        }
                    } catch (e) {
                        console.error("Failed to parse error JSON for get_smart_suggestions:", e);
                    }
                    smartSuggestionsDisplay.innerHTML = `<p class="error-message">${errorMessage}</p>`;
                }
            } catch (error) {
                console.error('Fetch error for get_smart_suggestions:', error);
                smartSuggestionsDisplay.innerHTML = `<p class="error-message">A network error occurred, or the server is unreachable. Please try again later.</p>`;
            } finally {
                getSmartSuggestionsButton.disabled = false;
                getSmartSuggestionsButton.textContent = originalButtonText;
            }
        });
    }

    // New: Translate Resume Feature Logic
    const translateResumeButton = document.getElementById('translateResumeButton');
    const resumeTextForTranslationInput = document.getElementById('resumeTextForTranslation');
    const targetLanguageSelect = document.getElementById('targetLanguage');
    const translatedResumeDisplay = document.getElementById('translatedResumeDisplay');

    if (translateResumeButton) {
        translateResumeButton.addEventListener('click', async () => {
            const originalButtonText = translateResumeButton.textContent;
            translateResumeButton.disabled = true;
            translateResumeButton.textContent = 'Translating...';
            translatedResumeDisplay.innerHTML = ''; // Clear previous

            const resumeText = resumeTextForTranslationInput.value.trim();
            const targetLanguage = targetLanguageSelect.value;

            if (!resumeText) {
                translatedResumeDisplay.textContent = 'Please paste the resume text for translation.';
                translatedResumeDisplay.style.color = 'red';
                translateResumeButton.disabled = false;
                translateResumeButton.textContent = originalButtonText;
                return;
            }
            if (!targetLanguage) {
                translatedResumeDisplay.textContent = 'Please select a target language.';
                translatedResumeDisplay.style.color = 'red';
                translateResumeButton.disabled = false;
                translateResumeButton.textContent = originalButtonText;
                return;
            }

            // translatedResumeDisplay.textContent = 'Translating resume...'; // Handled by button
            translatedResumeDisplay.style.color = '#333'; // Default text color for messages

            try {
                const response = await fetch('/translate_resume', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        resume_text: resumeText,
                        target_language: targetLanguage,
                    }),
                });

                if (response.ok) {
                    const data = await response.json();
                    let resultsHTML = `<h4>Translation Results:</h4>`;
                    resultsHTML += `<p><strong>Original Language (Detected):</strong> ${data.identified_language_code || 'N/A'}</p>`;
                    resultsHTML += `<p><strong>Target Language:</strong> ${data.target_language.toUpperCase()}</p>`;
                    resultsHTML += `<p><strong>Original Snippet:</strong></p>`;
                    resultsHTML += `<pre style="white-space: pre-wrap; word-wrap: break-word; background-color: #f8f9fa; padding: 10px; border: 1px solid #dee2e6; border-radius: 4px;">${data.original_text_snippet}</pre>`;
                    resultsHTML += `<p><strong>Translated Text:</strong></p>`;
                    resultsHTML += `<pre style="white-space: pre-wrap; word-wrap: break-word; background-color: #f0f0f0; padding: 10px; border-radius: 4px;">${data.translated_text}</pre>`;
                    translatedResumeDisplay.innerHTML = resultsHTML;
                    // translatedResumeDisplay.style.color = 'green'; // Color handled by CSS if needed
                } else {
                    let errorMessage = `Error: ${response.status} ${response.statusText}`;
                    try {
                        const errorData = await response.json();
                        if (errorData && errorData.error) {
                            errorMessage = errorData.error;
                        }
                    } catch (e) {
                        console.error("Failed to parse error JSON for translate_resume:", e);
                    }
                    translatedResumeDisplay.innerHTML = `<p class="error-message">${errorMessage}</p>`;
                }
            } catch (error) {
                console.error('Fetch error for translate_resume:', error);
                translatedResumeDisplay.innerHTML = `<p class="error-message">A network error occurred, or the server is unreachable. Please try again later.</p>`;
            } finally {
                translateResumeButton.disabled = false;
                translateResumeButton.textContent = originalButtonText;
            }
        });
    }

    // New: ATS Compatibility Check Logic
    const checkAtsButton = document.getElementById('checkAtsButton');
    const atsSuggestionsDisplay = document.getElementById('atsSuggestionsDisplay');
    // Re-use resumeUploadInput from the Resume Analyzer section
    // const resumeUploadInput = document.getElementById('resumeUpload');

    if (checkAtsButton) {
        checkAtsButton.addEventListener('click', async () => {
            const originalButtonText = checkAtsButton.textContent;
            checkAtsButton.disabled = true;
            checkAtsButton.textContent = 'Checking...';
            atsSuggestionsDisplay.innerHTML = ''; // Clear previous

            if (!resumeUploadInput || !resumeUploadInput.files || resumeUploadInput.files.length === 0) {
                atsSuggestionsDisplay.textContent = 'Please upload a resume first using the "Upload Your Resume" section.';
                atsSuggestionsDisplay.style.color = 'red';
                checkAtsButton.disabled = false;
                checkAtsButton.textContent = originalButtonText;
                return;
            }

            const file = resumeUploadInput.files[0];
            const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
            if (!allowedTypes.includes(file.type)) {
                atsSuggestionsDisplay.textContent = 'Invalid file type for ATS check. Please upload a PDF, DOC, DOCX, or TXT file.';
                atsSuggestionsDisplay.style.color = 'red';
                checkAtsButton.disabled = false;
                checkAtsButton.textContent = originalButtonText;
                return;
            }

            const formData = new FormData();
            formData.append('resume', file);

            // atsSuggestionsDisplay.textContent = 'Checking ATS compatibility...'; // Handled by button
            atsSuggestionsDisplay.style.color = '#333'; // Default text color for messages

            try {
                const response = await fetch('/check_ats', {
                    method: 'POST',
                    body: formData, // Sending as FormData for file upload
                });

                if (response.ok) {
                    const data = await response.json();
                    let resultsHTML = `<h4>ATS Compatibility Tips:</h4>`; // Added heading
                    resultsHTML += `<p><strong>${data.message}</strong></p>`; // Wrap message in <p>
                    if (data.suggestions && data.suggestions.length > 0) {
                        resultsHTML += `<ul>`; // Using unordered list
                        data.suggestions.forEach(suggestion => {
                            resultsHTML += `<li>${suggestion}</li>`;
                        });
                        resultsHTML += `</ul>`;
                    } else {
                        resultsHTML += `<p>No specific ATS tips available at this time.</p>`;
                    }
                    atsSuggestionsDisplay.innerHTML = resultsHTML;
                    atsSuggestionsDisplay.style.color = 'blue'; // Using blue for suggestions
                } else {
                    let errorMessage = `Error: ${response.status} ${response.statusText}`;
                    try {
                        const errorData = await response.json();
                        if (errorData && errorData.error) {
                            errorMessage = errorData.error;
                        }
                    } catch (e) {
                        console.error("Failed to parse error JSON for check_ats:", e);
                    }
                    atsSuggestionsDisplay.innerHTML = `<p class="error-message">${errorMessage}</p>`;
                }
            } catch (error) {
                console.error('Fetch error for check_ats:', error);
                atsSuggestionsDisplay.innerHTML = `<p class="error-message">A network error occurred, or the server is unreachable. Please try again later.</p>`;
            } finally {
                checkAtsButton.disabled = false;
                checkAtsButton.textContent = originalButtonText;
            }
        });
    }

    // Keep existing UI Interactivity from original script.js
    const uploadSection = document.querySelector(".upload-section");
    if (uploadSection) {
        uploadSection.addEventListener("mouseenter", () => {
            uploadSection.style.transform = "scale(1.02)"; // Slightly reduced scale
            uploadSection.style.transition = "transform 0.3s ease";
        });

        uploadSection.addEventListener("mouseleave", () => {
            uploadSection.style.transform = "scale(1)";
        });
    }

    // New: Job Match Feature Logic
    const jobMatchButton = document.getElementById('jobMatchButton');
    const jobDescriptionInput = document.getElementById('jobDescriptionInput');
    const jobMatchResultsDisplay = document.getElementById('jobMatchResultsDisplay');

    if (jobMatchButton) {
        jobMatchButton.addEventListener('click', async () => {
            const originalButtonText = jobMatchButton.textContent;
            jobMatchButton.disabled = true;
            jobMatchButton.textContent = 'Matching...';
            jobMatchResultsDisplay.innerHTML = ''; // Clear previous

            if (!jobDescriptionInput || jobDescriptionInput.value.trim() === '') {
                jobMatchResultsDisplay.textContent = 'Please paste a job description.';
                jobMatchResultsDisplay.style.color = 'red';
                jobMatchButton.disabled = false;
                jobMatchButton.textContent = originalButtonText;
                return;
            }

            const jobDescription = jobDescriptionInput.value.trim();

            if (!lastResumeAnalysisData) {
                jobMatchResultsDisplay.textContent = 'Please analyze your resume first to provide its keywords/entities for job matching.';
                jobMatchResultsDisplay.style.color = 'red';
                jobMatchButton.disabled = false;
                jobMatchButton.textContent = originalButtonText;
                return;
            }

            // jobMatchResultsDisplay.textContent = 'Analyzing job description and matching with resume...'; // Handled by button
            jobMatchResultsDisplay.style.color = '#333'; // Default text color for messages

            try {
                const response = await fetch('/match_job', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        job_description: jobDescription,
                        resume_keywords: lastResumeAnalysisData.keywords,
                        resume_entities: lastResumeAnalysisData.entities
                    }),
                });

                if (response.ok) {
                    const data = await response.json();
                    let resultsHTML = `<h3>Job Match Analysis</h3>`; // Main heading
                    resultsHTML += `<p><strong>Message:</strong> ${data.message}</p>`;

                    resultsHTML += `<h4>Overall Match</h4>`;
                    resultsHTML += `<p><strong>Match Score:</strong> ${data.match_score || 'N/A'}</p>`;

                    if (data.job_description_analysis) {
                        resultsHTML += `<h4>Job Description Analysis</h4>`;
                        if (data.job_description_analysis.keywords && data.job_description_analysis.keywords.length > 0) {
                            resultsHTML += `<h5>Keywords</h5><ul>`; // Removed colon
                            data.job_description_analysis.keywords.forEach(kw => {
                                resultsHTML += `<li><strong>${kw.text}</strong> (Relevance: ${kw.relevance ? kw.relevance.toFixed(2) : 'N/A'})</li>`;
                            });
                            resultsHTML += `</ul>`;
                        } else {
                            resultsHTML += `<p>No keywords extracted from job description.</p>`;
                        }
                        if (data.job_description_analysis.entities && data.job_description_analysis.entities.length > 0) {
                            resultsHTML += `<h5>Entities</h5><ul>`; // Removed colon
                            data.job_description_analysis.entities.forEach(entity => {
                                resultsHTML += `<li><strong>${entity.type}:</strong> ${entity.text} (Relevance: ${entity.relevance ? entity.relevance.toFixed(2) : 'N/A'})</li>`;
                            });
                            resultsHTML += `</ul>`;
                        } else {
                            resultsHTML += `<p>No entities extracted from job description.</p>`;
                        }
                    }

                    if (data.missing_resume_keywords && data.missing_resume_keywords.length > 0) {
                        resultsHTML += `<h4>Keywords Missing From Your Resume</h4><ul>`; // Removed colon
                        data.missing_resume_keywords.forEach(kwText => {
                            resultsHTML += `<li>${kwText}</li>`;
                        });
                        resultsHTML += `</ul>`;
                    } else {
                        resultsHTML += `<p>No significant keywords from the job description appear to be missing from your resume analysis data!</p>`;
                    }

                    if (data.ai_suggestions && data.ai_suggestions.length > 0) {
                        resultsHTML += `<h4>AI-Generated Suggestions</h4><ul>`; // Removed (Gemini) for brevity
                        data.ai_suggestions.forEach(suggestion => {
                            resultsHTML += `<li>${suggestion}</li>`;
                        });
                        resultsHTML += `</ul>`;
                    } else {
                        resultsHTML += `<p>No AI suggestions available at this time.</p>`;
                    }

                    jobMatchResultsDisplay.innerHTML = resultsHTML;
                    jobMatchResultsDisplay.style.color = 'initial';
                } else {
                    let errorMessage = `Error: ${response.status} ${response.statusText}`;
                    try {
                        const errorData = await response.json();
                        if (errorData && errorData.error) {
                            errorMessage = errorData.error;
                        }
                    } catch (e) {
                        console.error("Failed to parse error JSON for match_job:", e);
                    }
                    jobMatchResultsDisplay.innerHTML = `<p class="error-message">${errorMessage}</p>`;
                }
            } catch (error) {
                console.error('Fetch error for match_job:', error);
                jobMatchResultsDisplay.innerHTML = `<p class="error-message">A network error occurred, or the server is unreachable. Please try again later.</p>`;
            } finally {
                jobMatchButton.disabled = false;
                jobMatchButton.textContent = originalButtonText;
            }
        });
    }
});
