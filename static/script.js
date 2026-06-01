/**
 * Dr. B. B. Hegde First Grade College – Admission Form Scripts
 * Handles form submission via AJAX, PIN code auto-tab, and modal interactions.
 */

document.addEventListener('DOMContentLoaded', () => {

    // ===========================
    // PIN CODE AUTO-TAB
    // ===========================
    const pinBoxes = document.querySelectorAll('.pin-box');
    pinBoxes.forEach((box, index) => {
        box.addEventListener('input', (e) => {
            const val = e.target.value;
            // Allow only digits
            e.target.value = val.replace(/\D/g, '');
            if (val && index < pinBoxes.length - 1) {
                pinBoxes[index + 1].focus();
            }
        });

        box.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !e.target.value && index > 0) {
                pinBoxes[index - 1].focus();
            }
        });

        // Select all text on focus for easy overwrite
        box.addEventListener('focus', () => {
            box.select();
        });
    });

    // ===========================
    // AADHAR FORMATTING (XXXX XXXX XXXX)
    // ===========================
    const aadharField = document.getElementById('aadhar');
    if (aadharField) {
        aadharField.addEventListener('input', (e) => {
            let value = e.target.value.replace(/\D/g, '').slice(0, 12);
            let formatted = value.replace(/(\d{4})(?=\d)/g, '$1 ');
            e.target.value = formatted;
        });
    }

    // ===========================
    // FORM VALIDATION
    // ===========================
    function getFieldLabel(field) {
        if (field.id) {
            const label = form.querySelector(`label[for="${field.id}"]`);
            if (label) return label.textContent.trim();
        }
        if (field.dataset.label) return field.dataset.label.trim();
        if (field.placeholder) return field.placeholder.trim();
        return field.name.replace(/[_-]/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
    }

    function validateForm() {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        // Reset previous errors
        document.querySelectorAll('.field-error').forEach(el => el.classList.remove('field-error'));
        document.querySelectorAll('.section-error').forEach(el => {
            el.classList.remove('section-error');
            el.classList.remove('shake');
        });

        const errorSections = new Set();
        const missingFields = [];
        const validatedRadioGroups = new Set();
        let firstErrorField = null;

        requiredFields.forEach(field => {
            let isFieldEmpty = false;
            
            // Handle radio groups (validate each group once)
            if (field.type === 'radio') {
                if (validatedRadioGroups.has(field.name)) return;
                validatedRadioGroups.add(field.name);
                const group = form.querySelectorAll(`input[name="${field.name}"]:checked`);
                if (group.length === 0) isFieldEmpty = true;
            } else if (field.type === 'file') {
                // Document uploads are optional
                isFieldEmpty = false;
            } else if (field.tagName === 'SELECT') {
                if (!field.value) isFieldEmpty = true;
            } else if (!field.value.trim()) {
                isFieldEmpty = true;
            }

            if (isFieldEmpty) {
                isValid = false;
                field.classList.add('field-error');
                
                const fieldLabel = getFieldLabel(field);
                if (fieldLabel && !missingFields.includes(fieldLabel)) {
                    missingFields.push(fieldLabel);
                }

                // Find the parent section card
                const section = field.closest('.form-section');
                if (section) errorSections.add(section);
                
                if (!firstErrorField) firstErrorField = field;
            }
        });

        // Highlight sections with errors
        errorSections.forEach(section => {
            section.classList.add('section-error');
        });

        if (!isValid) {
            // Shake the first error section and scroll to it
            const firstSection = Array.from(errorSections)[0];
            if (firstSection) {
                firstSection.classList.add('shake');
                firstSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            // Highlight button as well
            if (submitBtn) {
                submitBtn.classList.add('btn-error');
                setTimeout(() => submitBtn.classList.remove('btn-error'), 600);
            }

            const missingListHtml = missingFields.slice(0, 8).map(fieldName => `<li>${fieldName}</li>`).join('');
            const moreText = missingFields.length > 8 ? `<li>...and ${missingFields.length - 8} more fields</li>` : '';
            showToast(`Please fill in the following required fields:<ul style="margin:0.5rem 0 0 18px; padding:0; list-style:disc;">${missingListHtml}${moreText}</ul>`, 'error');
        }

        return isValid;
    }

    // ===========================
    // FORM SUBMISSION (AJAX)
    // ===========================
    const form = document.getElementById('admission-form');
    const submitBtn = document.getElementById('submitBtn');
    const modal = document.getElementById('success-modal');
    const closeModalBtn = document.getElementById('close-modal');
    const modalAppNo = document.getElementById('modal-app-no');

    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Perform manual validation (DOB uses #dob-day, #dob-month, #dob-year selects directly)
            if (!validateForm()) return;

            // Add loading state
            submitBtn.classList.add('loading');
            submitBtn.disabled = true;

            try {
                const formData = new FormData(form);
                const response = await fetch('/submit', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (result.success) {
                    // Update modal with app number
                    if (modalAppNo) {
                        modalAppNo.textContent = result.application_no;
                    }
                    // Show success modal
                    if (modal) {
                        modal.classList.add('active');
                    }
                    // Reset form
                    form.reset();
                    // Clear any lingering error classes
                    document.querySelectorAll('.section-error').forEach(el => el.classList.remove('section-error'));
                } else {
                    showToast(result.message || 'Submission failed. Please try again.', 'error');
                }
            } catch (error) {
                console.error('Submission error:', error);
                showToast('Network error. Please check your connection and try again.', 'error');
            } finally {
                submitBtn.classList.remove('loading');
                submitBtn.disabled = false;
            }
        });
    }

    // ===========================
    // MODAL CLOSE
    // ===========================
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            modal.classList.remove('active');
            // Reload page to get a new application number
            window.location.reload();
        });
    }

    // Close modal on overlay click
    if (modal) {
        const overlay = modal.querySelector('.modal-overlay');
        if (overlay) {
            overlay.addEventListener('click', () => {
                modal.classList.remove('active');
                window.location.reload();
            });
        }
    }

    // ===========================
    // DOCUMENT UPLOAD AND PREVIEW ACTIONS
    // ===========================
    const selectedFiles = {};

    document.querySelectorAll('.upload-btn').forEach(button => {
        button.addEventListener('click', () => {
            const item = button.closest('.checklist-item');
            if (!item) return;
            const fileInput = item.querySelector('input.hidden-file-input');
            if (fileInput) fileInput.click();
        });
    });

    document.querySelectorAll('.show-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            const item = button.closest('.checklist-item');
            if (!item) return;
            const fileInput = item.querySelector('input.hidden-file-input');
            if (fileInput && fileInput.files && fileInput.files.length > 0) {
                e.preventDefault();
                const file = fileInput.files[0];
                const fileURL = URL.createObjectURL(file);
                window.open(fileURL, '_blank');
            }
        });
    });

    document.querySelectorAll('.hidden-file-input').forEach(input => {
        input.addEventListener('change', () => {
            const item = input.closest('.checklist-item');
            if (!item) return;
            
            const showBtn = item.querySelector('.show-btn');
            const label = item.querySelector('.file-name');
            
            if (input.files && input.files.length > 0) {
                // Store the selected file
                selectedFiles[input.name] = input.files[0];
            } else if (selectedFiles[input.name]) {
                // Restore the previously selected file
                try {
                    const dt = new DataTransfer();
                    dt.items.add(selectedFiles[input.name]);
                    input.files = dt.files;
                } catch (e) {
                    console.error('Failed to restore file:', e);
                }
            }
            
            if (input.files && input.files.length > 0) {
                const fileName = input.files[0].name;
                if (label) {
                    label.textContent = fileName;
                    label.style.display = 'inline-block'; // show the filename so the user knows what was selected
                }
                if (showBtn) {
                    showBtn.style.display = 'inline-block'; // show the "Show" button instead
                }
            } else {
                if (label) {
                    label.textContent = 'No file selected';
                    label.style.display = 'inline-block';
                }
                if (showBtn) {
                    showBtn.style.display = 'none';
                }
            }

            const checkbox = item.querySelector('input[type="checkbox"]');
            if (checkbox) {
                checkbox.checked = !!(input.files && input.files.length);
            }
        });
    });

    // ===========================
    // TOAST NOTIFICATIONS
    // ===========================
    function showToast(message, type = 'info') {
        // Remove any existing toast
        const existing = document.querySelector('.toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-message">${message}</span>
            <button class="toast-close">&times;</button>
        `;

        // Style the toast
        Object.assign(toast.style, {
            position: 'fixed',
            bottom: '32px',
            right: '32px',
            zIndex: '2000',
            padding: '16px 24px',
            borderRadius: '12px',
            background: type === 'error'
                ? 'rgba(248, 113, 113, 0.15)'
                : 'rgba(96, 165, 250, 0.15)',
            border: `1px solid ${type === 'error' ? 'rgba(248,113,113,0.3)' : 'rgba(96,165,250,0.3)'}`,
            color: type === 'error' ? '#f87171' : '#60a5fa',
            fontSize: '0.88rem',
            fontWeight: '600',
            fontFamily: "'Inter', sans-serif",
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            backdropFilter: 'blur(12px)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            animation: 'fadeInUp 0.4s ease',
            maxWidth: '400px'
        });

        document.body.appendChild(toast);

        // Close button
        toast.querySelector('.toast-close').addEventListener('click', () => {
            toast.style.animation = 'fadeIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        });

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(10px)';
                toast.style.transition = 'all 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }
        }, 5000);
    }

    // ===========================
    // AUTO-CALCULATE PERCENTAGE FOR QUALIFYING EXAM
    // ===========================
    const marksInput = document.querySelector('input[name="qual-exam-marks"]');
    const maxInput = document.querySelector('input[name="qual-exam-max"]');
    const percentInput = document.querySelector('input[name="qual-exam-percent"]');

    if (marksInput && maxInput && percentInput) {
        const calculatePercentage = () => {
            const marks = parseFloat(marksInput.value);
            const max = parseFloat(maxInput.value);

            if (!isNaN(marks) && !isNaN(max) && max > 0) {
                const percentage = (marks / max) * 100;
                percentInput.value = percentage.toFixed(2) + '%';
            } else {
                percentInput.value = '';
            }
        };

        marksInput.addEventListener('input', calculatePercentage);
        maxInput.addEventListener('input', calculatePercentage);
    }

    // ===========================
    // APPLICATION PROGRESS (fills step-by-step as user completes sections)
    // ===========================
    const progressFill = document.getElementById('progressFill');
    const progressPct = document.getElementById('progress-percent');
    const stepItems = document.querySelectorAll('.step-item');
    const progressSections = Array.from(stepItems).map(item => ({
        stepEl: item,
        sectionEl: document.getElementById(item.dataset.section)
    })).filter(entry => entry.sectionEl);

    let lastCompletedCount = 0;

    function fieldHasValue(field) {
        if (!field || field.disabled) return false;
        if (field.type === 'file') {
            return field.files && field.files.length > 0;
        }
        if (field.type === 'radio' || field.type === 'checkbox') {
            return field.checked;
        }
        if (field.tagName === 'SELECT') {
            return !!field.value;
        }
        return !!String(field.value || '').trim();
    }

    function radioGroupFilled(form, name) {
        return !!form.querySelector(`input[name="${name}"]:checked`);
    }

    function allFieldsFilled(form, names) {
        return names.every(name => {
            const field = form.querySelector(`[name="${name}"]`);
            if (!field) return false;
            if (field.type === 'radio') {
                return radioGroupFilled(form, name);
            }
            return fieldHasValue(field);
        });
    }

    function pinCodeFilled(form) {
        return Array.from({ length: 6 }, (_, i) => form.querySelector(`[name="pin_${i + 1}"]`))
            .every(box => box && /^\d$/.test(box.value.trim()));
    }

    const PRIOR_SECTION_IDS = [
        'section1', 'section4', 'section5', 'section6', 'section7',
        'section8', 'section9', 'section10', 'section11'
    ];

    function checkSectionById(id) {
        if (!form) return false;
        switch (id) {
            case 'section1':
                return allFieldsFilled(form, ['name', 'whatsapp', 'gender', 'dob-date', 'dob-month', 'dob-year']);
            case 'section4':
                return allFieldsFilled(form, ['nationality', 'email']);
            case 'section5':
                return allFieldsFilled(form, ['village', 'taluk', 'district']);
            case 'section6':
                return allFieldsFilled(form, ['religion', 'caste']);
            case 'section7':
                return radioGroupFilled(form, 'category');
            case 'section8':
                return allFieldsFilled(form, ['parent-name', 'postal-address']) && pinCodeFilled(form);
            case 'section9':
                return radioGroupFilled(form, 'program') && radioGroupFilled(form, 'language');
            case 'section10':
                return allFieldsFilled(form, ['college-attended']);
            case 'section11':
                return allFieldsFilled(form, [
                    'qual-exam-reg-no',
                    'qual-exam-year',
                    'qual-exam-board',
                    'qual-exam-marks',
                    'qual-exam-max'
                ]);
            case 'section12':
                return PRIOR_SECTION_IDS.every(sid => checkSectionById(sid));
            default:
                return false;
        }
    }

    function isSectionComplete(sectionEl) {
        if (!sectionEl) return false;
        return checkSectionById(sectionEl.id);
    }

    function getSequentialProgress() {
        let completedCount = 0;
        for (let i = 0; i < progressSections.length; i++) {
            if (isSectionComplete(progressSections[i].sectionEl)) {
                completedCount++;
            } else {
                break;
            }
        }
        return completedCount;
    }

    function updateApplicationProgress() {
        if (!progressFill || !progressPct || !progressSections.length) return;

        const completedCount = getSequentialProgress();
        const totalSteps = progressSections.length;
        const activeIndex = Math.min(completedCount, totalSteps - 1);
        const percent = Math.round((completedCount / totalSteps) * 100);

        progressFill.style.width = percent + '%';
        progressPct.textContent = percent + '%';

        progressSections.forEach((entry, i) => {
            entry.stepEl.classList.remove('active', 'completed');
            if (i < completedCount) {
                entry.stepEl.classList.add('completed');
            } else if (i === activeIndex) {
                entry.stepEl.classList.add('active');
            }
        });

        if (completedCount > lastCompletedCount && completedCount < totalSteps) {
            const nextSection = progressSections[completedCount].sectionEl;
            if (nextSection) {
                setTimeout(() => {
                    nextSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 280);
            }
        }
        lastCompletedCount = completedCount;
    }

    if (form && progressSections.length) {
        let progressTimer;
        const scheduleProgressUpdate = () => {
            clearTimeout(progressTimer);
            progressTimer = setTimeout(updateApplicationProgress, 120);
        };

        form.addEventListener('input', scheduleProgressUpdate);
        form.addEventListener('change', scheduleProgressUpdate);

        stepItems.forEach(item => {
            item.addEventListener('click', () => {
                const target = document.getElementById(item.dataset.section);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });

        updateApplicationProgress();
    }

    // ===========================
    // INTERSECTION OBSERVER FOR ANIMATIONS
    // ===========================
    const sections = document.querySelectorAll('.form-section');
    if (sections.length > 0 && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animationPlayState = 'running';
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        sections.forEach(section => {
            section.style.animationPlayState = 'paused';
            observer.observe(section);
        });
    }

});
