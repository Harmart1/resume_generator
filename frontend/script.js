document.addEventListener("DOMContentLoaded", () => {
    let currentUserTier = "free"; // Default user tier
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
    const resumeUploadInput = document.getElementById('resumeUpload');
    const resultsDisplay = document.getElementById('results-display');

    if (analyzeButton) {
        analyzeButton.addEventListener('click', async () => {
            if (!resumeUploadInput || !resumeUploadInput.files || resumeUploadInput.files.length === 0) {
                resultsDisplay.textContent = 'Please select a resume file first.';
                resultsDisplay.style.color = 'red';
                return;
            }

            const file = resumeUploadInput.files[0];
            const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];

            if (!allowedTypes.includes(file.type)) {
                resultsDisplay.textContent = 'Invalid file type. Please upload a PDF, DOC, DOCX, or TXT file.';
                resultsDisplay.style.color = 'red';
                return;
            }

            const formData = new FormData();
            formData.append('resume', file);

            resultsDisplay.textContent = 'Analyzing...';
            resultsDisplay.style.color = '#333'; // Default text color

            try {
                const response = await fetch('/analyze_resume', {
                    method: 'POST',
                    body: formData,
                });

                if (response.ok) {
                    const data = await response.json();
                    // Displaying the mock analysis results
                    let resultsHTML = `<strong>${data.message}</strong><br>Filename: ${data.filename}`;
                    if (data.keywords_found) {
                        resultsHTML += `<br>Keywords Found: ${data.keywords_found.join(', ')}`;
                    }
                    resultsDisplay.innerHTML = resultsHTML;
                    resultsDisplay.style.color = 'green';
                } else {
                    const errorData = await response.json();
                    resultsDisplay.textContent = `Error: ${errorData.error || response.statusText}`;
                    resultsDisplay.style.color = 'red';
                }
            } catch (error) {
                console.error('Error sending file:', error);
                resultsDisplay.textContent = 'An error occurred while sending the file. Please try again.';
                resultsDisplay.style.color = 'red';
            }
        });
    }

    // New: Job Market Insights (AI Jules) Feature Logic
    const getJobMarketInsightsButton = document.getElementById('getJobMarketInsightsButton');
    const jobMarketInsightsDisplay = document.getElementById('jobMarketInsightsDisplay');
    // Re-use resumeUploadInput from the Resume Analyzer section for file access

    if (getJobMarketInsightsButton) {
        getJobMarketInsightsButton.addEventListener('click', async () => {
            if (!resumeUploadInput || !resumeUploadInput.files || resumeUploadInput.files.length === 0) {
                jobMarketInsightsDisplay.textContent = 'Please upload a resume first using the "Upload Your Resume" section.';
                jobMarketInsightsDisplay.style.color = 'red';
                return;
            }

            const file = resumeUploadInput.files[0];
            const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
            if (!allowedTypes.includes(file.type)) {
                jobMarketInsightsDisplay.textContent = 'Invalid file type for Job Market Insights. Please upload a PDF, DOC, DOCX, or TXT file.';
                jobMarketInsightsDisplay.style.color = 'red';
                return;
            }

            const formData = new FormData();
            formData.append('resume', file);
            formData.append('user_tier', currentUserTier); // Add user tier

            jobMarketInsightsDisplay.textContent = 'Fetching job market insights...';
            jobMarketInsightsDisplay.style.color = '#333'; // Default text color

            try {
                const response = await fetch('/get_job_market_insights', {
                    method: 'POST',
                    body: formData,
                });

                if (response.ok) {
                    const data = await response.json();
                    let resultsHTML = `<strong>${data.message}</strong>`;
                    if (data.insights && data.insights.length > 0) {
                        resultsHTML += `<br><br><strong>Job Market Insights (from AI Jules):</strong><ul>`;
                        data.insights.forEach(insight => {
                            resultsHTML += `<li>${insight}</li>`;
                        });
                        resultsHTML += `</ul>`;
                    }
                    if (data.trending_jobs && data.trending_jobs.length > 0) {
                        resultsHTML += `<br><strong>Trending Jobs for your profile:</strong> ${data.trending_jobs.join(', ')}`;
                    }
                    jobMarketInsightsDisplay.innerHTML = resultsHTML;
                    jobMarketInsightsDisplay.style.color = '#0077b6'; // A different blue color
                } else {
                    const errorData = await response.json();
                    jobMarketInsightsDisplay.textContent = `Error: ${errorData.error || response.statusText}`;
                    jobMarketInsightsDisplay.style.color = 'red';
                }
            } catch (error) {
                console.error('Error fetching job market insights:', error);
                jobMarketInsightsDisplay.textContent = 'An error occurred while fetching job market insights. Please try again.';
                jobMarketInsightsDisplay.style.color = 'red';
            }
        });
    }

    // New: Smart Suggestions (AI Jules) Feature Logic
    const getSmartSuggestionsButton = document.getElementById('getSmartSuggestionsButton');
    const smartSuggestionsDisplay = document.getElementById('smartSuggestionsDisplay');
    // Re-use resumeUploadInput from the Resume Analyzer section for file access

    if (getSmartSuggestionsButton) {
        getSmartSuggestionsButton.addEventListener('click', async () => {
            if (!resumeUploadInput || !resumeUploadInput.files || resumeUploadInput.files.length === 0) {
                smartSuggestionsDisplay.textContent = 'Please upload a resume first using the "Upload Your Resume" section.';
                smartSuggestionsDisplay.style.color = 'red';
                return;
            }

            const file = resumeUploadInput.files[0];
            const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
            if (!allowedTypes.includes(file.type)) {
                smartSuggestionsDisplay.textContent = 'Invalid file type for Smart Suggestions. Please upload a PDF, DOC, DOCX, or TXT file.';
                smartSuggestionsDisplay.style.color = 'red';
                return;
            }

            const formData = new FormData();
            formData.append('resume', file);
            formData.append('user_tier', currentUserTier); // Add user tier

            smartSuggestionsDisplay.textContent = 'Generating smart suggestions...';
            smartSuggestionsDisplay.style.color = '#333'; // Default text color

            try {
                const response = await fetch('/get_smart_suggestions', {
                    method: 'POST',
                    body: formData,
                });

                if (response.ok) {
                    const data = await response.json();
                    let resultsHTML = `<strong>${data.message}</strong>`;
                    if (data.suggestions && data.suggestions.length > 0) {
                        resultsHTML += `<br><br><strong>Smart Suggestions (from AI Jules):</strong><ul>`;
                        data.suggestions.forEach(suggestion => {
                            resultsHTML += `<li>${suggestion}</li>`;
                        });
                        resultsHTML += `</ul>`;
                    }
                    smartSuggestionsDisplay.innerHTML = resultsHTML;
                    smartSuggestionsDisplay.style.color = '#5a0099'; // A distinct purple color
                } else {
                    const errorData = await response.json();
                    smartSuggestionsDisplay.textContent = `Error: ${errorData.error || response.statusText}`;
                    smartSuggestionsDisplay.style.color = 'red';
                }
            } catch (error) {
                console.error('Error fetching smart suggestions:', error);
                smartSuggestionsDisplay.textContent = 'An error occurred while fetching smart suggestions. Please try again.';
                smartSuggestionsDisplay.style.color = 'red';
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
            const resumeText = resumeTextForTranslationInput.value.trim();
            const targetLanguage = targetLanguageSelect.value;

            if (!resumeText) {
                translatedResumeDisplay.textContent = 'Please paste the resume text for translation.';
                translatedResumeDisplay.style.color = 'red';
                return;
            }
            if (!targetLanguage) {
                translatedResumeDisplay.textContent = 'Please select a target language.';
                translatedResumeDisplay.style.color = 'red';
                return;
            }

            translatedResumeDisplay.textContent = 'Translating resume...';
            translatedResumeDisplay.style.color = '#333'; // Default text color

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
                    translatedResumeDisplay.textContent = `Translation to ${data.target_language.toUpperCase()}:\n\n${data.translated_text}`;
                    translatedResumeDisplay.style.color = 'green'; // Or a neutral color
                } else {
                    const errorData = await response.json();
                    translatedResumeDisplay.textContent = `Error: ${errorData.error || response.statusText}`;
                    translatedResumeDisplay.style.color = 'red';
                }
            } catch (error) {
                console.error('Error translating resume:', error);
                translatedResumeDisplay.textContent = 'An error occurred during translation. Please try again.';
                translatedResumeDisplay.style.color = 'red';
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
            if (!resumeUploadInput || !resumeUploadInput.files || resumeUploadInput.files.length === 0) {
                atsSuggestionsDisplay.textContent = 'Please upload a resume first using the "Upload Your Resume" section.';
                atsSuggestionsDisplay.style.color = 'red';
                return;
            }

            const file = resumeUploadInput.files[0];
            // Basic file type validation can be repeated here if desired, or assumed from previous upload
            const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
            if (!allowedTypes.includes(file.type)) {
                atsSuggestionsDisplay.textContent = 'Invalid file type for ATS check. Please upload a PDF, DOC, DOCX, or TXT file.';
                atsSuggestionsDisplay.style.color = 'red';
                return;
            }

            const formData = new FormData();
            formData.append('resume', file);

            atsSuggestionsDisplay.textContent = 'Checking ATS compatibility...';
            atsSuggestionsDisplay.style.color = '#333'; // Default text color

            try {
                const response = await fetch('/check_ats', {
                    method: 'POST',
                    body: formData, // Sending as FormData for file upload
                });

                if (response.ok) {
                    const data = await response.json();
                    let resultsHTML = `<strong>${data.message}</strong>`;
                    if (data.suggestions && data.suggestions.length > 0) {
                        resultsHTML += `<br><br><strong>ATS Suggestions:</strong><ul>`;
                        data.suggestions.forEach(suggestion => {
                            resultsHTML += `<li>${suggestion}</li>`;
                        });
                        resultsHTML += `</ul>`;
                    }
                    atsSuggestionsDisplay.innerHTML = resultsHTML;
                    atsSuggestionsDisplay.style.color = 'blue'; // Using blue for suggestions
                } else {
                    const errorData = await response.json();
                    atsSuggestionsDisplay.textContent = `Error: ${errorData.error || response.statusText}`;
                    atsSuggestionsDisplay.style.color = 'red';
                }
            } catch (error) {
                console.error('Error sending file for ATS check:', error);
                atsSuggestionsDisplay.textContent = 'An error occurred while checking ATS compatibility. Please try again.';
                atsSuggestionsDisplay.style.color = 'red';
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
            if (!jobDescriptionInput || jobDescriptionInput.value.trim() === '') {
                jobMatchResultsDisplay.textContent = 'Please paste a job description.';
                jobMatchResultsDisplay.style.color = 'red';
                return;
            }

            const jobDescription = jobDescriptionInput.value.trim();

            jobMatchResultsDisplay.textContent = 'Analyzing job description...';
            jobMatchResultsDisplay.style.color = '#333'; // Default text color

            try {
                const response = await fetch('/match_job', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ job_description: jobDescription }),
                });

                if (response.ok) {
                    const data = await response.json();
                    let resultsHTML = `<strong>${data.message}</strong><br>Match Score: ${data.match_score}`;
                    if (data.suggestions && data.suggestions.length > 0) {
                        resultsHTML += `<br><br><strong>Suggestions:</strong><ul>`;
                        data.suggestions.forEach(suggestion => {
                            resultsHTML += `<li>${suggestion}</li>`;
                        });
                        resultsHTML += `</ul>`;
                    }
                    jobMatchResultsDisplay.innerHTML = resultsHTML;
                    jobMatchResultsDisplay.style.color = 'green';
                } else {
                    const errorData = await response.json();
                    jobMatchResultsDisplay.textContent = `Error: ${errorData.error || response.statusText}`;
                    jobMatchResultsDisplay.style.color = 'red';
                }
            } catch (error) {
                console.error('Error sending job description:', error);
                jobMatchResultsDisplay.textContent = 'An error occurred while sending the job description. Please try again.';
                jobMatchResultsDisplay.style.color = 'red';
            }
        });
    }
});
