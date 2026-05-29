document.addEventListener('DOMContentLoaded', () => {
    const passwordInput = document.getElementById('password');
    const passwordToggleBtn = document.getElementById('toggle-password');
    const loginForm = document.getElementById('login-form');
    const submitBtn = document.getElementById('submit-btn');

    // Password visibility toggle
    if (passwordToggleBtn && passwordInput) {
        passwordToggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Toggle types
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            // Toggle icon
            const icon = passwordToggleBtn.querySelector('i');
            if (icon) {
                if (type === 'text') {
                    icon.classList.remove('fa-eye');
                    icon.classList.add('fa-eye-slash');
                } else {
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                }
            }
        });
    }

    // Input interactive micro-animations (e.g., adding classes or handling floating)
    const inputs = document.querySelectorAll('.form-input');
    inputs.forEach(input => {
        // Focus style tweaks or telemetry if needed
        input.addEventListener('focus', () => {
            input.parentElement.classList.add('is-focused');
        });
        input.addEventListener('blur', () => {
            input.parentElement.classList.remove('is-focused');
        });
    });

    // Form submission animation states
    if (loginForm && submitBtn) {
        loginForm.addEventListener('submit', (e) => {
            // Simple validation check before showing loader
            const emailInput = document.getElementById('email');
            if (emailInput.value.trim() !== '' && passwordInput.value.trim() !== '') {
                submitBtn.classList.add('loading');
                submitBtn.setAttribute('disabled', 'true');
            }
        });
    }
});
