document.addEventListener('DOMContentLoaded', () => {
    bindDeleteConfirmation();
    bindStatusQuickActions();
    bindRejectConfirmations();
    bindThemeToggle();
});

let activeConfirmCleanup = null;

function showCustomConfirm(message, onOk) {
    const modal = document.getElementById('custom-confirm-modal');
    if (!modal) {
        if (confirm(message)) {
            onOk();
        }
        return;
    }

    if (activeConfirmCleanup) {
        activeConfirmCleanup();
    }

    // Set custom message
    modal.querySelector('.messagebox-message').textContent = message;
    modal.classList.add('active');

    const okBtn = document.getElementById('confirm-ok-btn');
    const cancelBtn = document.getElementById('confirm-cancel-btn');
    const closeBtnX = document.getElementById('confirm-cancel-btn-x');

    const cleanup = () => {
        okBtn.removeEventListener('click', handleOk);
        cancelBtn.removeEventListener('click', handleCancel);
        closeBtnX.removeEventListener('click', handleCancel);
        modal.classList.remove('active');
        activeConfirmCleanup = null;
    };

    function handleOk() {
        cleanup();
        onOk();
    }

    function handleCancel() {
        cleanup();
    }

    okBtn.addEventListener('click', handleOk);
    cancelBtn.addEventListener('click', handleCancel);
    closeBtnX.addEventListener('click', handleCancel);

    activeConfirmCleanup = cleanup;
}

function bindDeleteConfirmation() {
    document.querySelectorAll('[data-confirm]').forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            const message = button.dataset.confirm;
            // Use custom messagebox confirmation for a consistent premium feel
            showCustomConfirm(message, () => {
                const form = button.closest('form');
                if (form) {
                    // Create input for action to match delete value
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = button.getAttribute('name') || 'action';
                    input.value = button.getAttribute('value') || '';
                    form.appendChild(input);
                    form.submit();
                }
            });
        });
    });
}

function bindStatusQuickActions() {
    document.querySelectorAll('[data-status-action]').forEach(button => {
        button.addEventListener('click', async event => {
            const form = button.closest('form');
            if (!form) return;
            const status = button.dataset.statusAction;
            form.querySelector('[name="status"]').value = status;
            form.submit();
        });
    });
}

function bindRejectConfirmations() {
    // Intercept quick action forms
    document.querySelectorAll('.reject-form').forEach(form => {
        form.addEventListener('submit', event => {
            event.preventDefault();
            showCustomConfirm('Are you sure you want to reject this applicant?', () => {
                form.submit();
            });
        });
    });

    // Intercept full detail panel admin form if changing status to rejected
    document.querySelectorAll('.detail-admin-form').forEach(form => {
        form.addEventListener('submit', event => {
            const submitter = event.submitter;
            if (submitter && submitter.getAttribute('name') === 'action' && submitter.getAttribute('value') === 'delete') {
                return; // Delete is already handled by standard delete confirmation
            }

            const statusSelect = form.querySelector('select[name="status"]');
            if (statusSelect && statusSelect.value === 'rejected') {
                event.preventDefault();
                showCustomConfirm('Are you sure you want to reject this applicant?', () => {
                    form.submit();
                });
            }
        });
    });
}

function bindThemeToggle() {
    const themeBtn = document.getElementById('themeToggleBtn');
    
    // Check if dark theme was previously saved in localStorage
    const savedTheme = localStorage.getItem('prarambha_admin_theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }

    if (themeBtn) {
        themeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            document.body.classList.toggle('dark-theme');
            
            if (document.body.classList.contains('dark-theme')) {
                localStorage.setItem('prarambha_admin_theme', 'dark');
            } else {
                localStorage.setItem('prarambha_admin_theme', 'light');
            }
        });
    }
}

