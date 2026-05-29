/* Prarambha Admin - Logic System */

document.addEventListener('DOMContentLoaded', () => {
    initBilingual();
    initCounters();
    initSeatSelection();
});

// 1. Bilingual Engine
const translations = {
    en: {
        dashboard: "Dashboard",
        applications: "Applications",
        seats: "Seat Allocation",
        courses: "Courses",
        total_apps: "Total Applications",
        approved: "Approved",
        pending: "Pending",
        available_seats: "Seats Available",
        approve: "Approve",
        reject: "Reject",
    },
    kn: {
        dashboard: "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
        applications: "ಅರ್ಜಿಗಳು",
        seats: "ಸೀಟು ಹಂಚಿಕೆ",
        courses: "ಕೋರ್ಸ್‌ಗಳು",
        total_apps: "ಒಟ್ಟು ಅರ್ಜಿಗಳು",
        approved: "ಅನುಮೋದಿಸಲಾಗಿದೆ",
        pending: "ಬಾಕಿ ಉಳಿದಿದೆ",
        available_seats: "ಲಭ್ಯವಿರುವ ಸೀಟುಗಳು",
        approve: "ಅನುಮೋದಿಸಿ",
        reject: "ತಿರಸ್ಕರಿಸಿ",
    }
};

let currentLang = localStorage.getItem('lang') || 'en';

function toggleLanguage() {
    currentLang = currentLang === 'en' ? 'kn' : 'en';
    localStorage.setItem('lang', currentLang);
    updateUIStrings();
}

function updateUIStrings() {
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[currentLang][key]) {
            el.textContent = translations[currentLang][key];
        }
    });
}

function initBilingual() {
    updateUIStrings();
    const toggleBtn = document.getElementById('lang-toggle');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleLanguage);
    }
}

// 2. Animated Counters
function initCounters() {
    const counters = document.querySelectorAll('.counter-val');
    counters.forEach(counter => {
        const target = +counter.getAttribute('data-target');
        const increment = target / 50; // Dynamic speed
        
        let count = 0;
        const updateCount = () => {
            if (count < target) {
                count += increment;
                counter.innerText = Math.ceil(count);
                setTimeout(updateCount, 20);
            } else {
                counter.innerText = target;
            }
        };
        updateCount();
    });
}

// 3. AJAX Seat Allocation
let selectedSeatId = null;

function initSeatSelection() {
    const seats = document.querySelectorAll('.seat.available');
    seats.forEach(seat => {
        seat.addEventListener('click', () => {
            // Toggle selection UI
            seats.forEach(s => s.classList.remove('selected'));
            seat.classList.add('selected');
            selectedSeatId = seat.getAttribute('data-id');
            showAllocationPanel(selectedSeatId);
        });
    });
}

function showAllocationPanel(seatId) {
    // This would typically open a modal to select a student
    console.log(`Setting up allocation for seat: ${seatId}`);
}

async function assignSeat(studentId, seatId) {
    try {
        const response = await fetch('/admin/assign-seat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_id: studentId, seat_id: seatId })
        });
        
        const data = await response.json();
        if (data.success) {
            const seatEl = document.querySelector(`.seat[data-id="${seatId}"]`);
            seatEl.classList.remove('available');
            seatEl.classList.add('occupied');
            seatEl.title = `Assigned to ID: ${studentId}`;
            alert("Seat assigned successfully!");
        } else {
            alert("Error: " + data.message);
        }
    } catch (err) {
        console.error("Failed to assign seat:", err);
    }
}

// 4. Application Actions
async function updateApplicationStatus(appId, status) {
    const confirmMsg = `Are you sure you want to ${status} this application?`;
    if (!confirm(confirmMsg)) return;

    try {
        const response = await fetch(`/admin/application/${status}/${appId}`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.success) {
            location.reload(); // Simple refresh for state sync
        } else {
            alert("Update failed: " + data.message);
        }
    } catch (err) {
        alert("Server error. Please check console.");
    }
}

// 5. Student Details Modal Logic
async function showStudentDetails(studentId) {
    const modal = document.getElementById('studentDetailModal');
    const content = document.getElementById('modalContent');
    
    // Reset and show modal with loading state
    content.innerHTML = `
        <div class="modal-loading">
            <div class="spinner"></div>
            <p style="margin-top: 1rem; color: var(--text-dim);">Fetching profile data...</p>
        </div>
    `;
    modal.classList.add('active');

    try {
        const response = await fetch(`/admin/student/${studentId}`);
        const data = await response.json();

        if (data.error) throw new Error(data.error);

        // Inject HTML
        content.innerHTML = `
            <div class="detail-header">
                <h2 style="color: var(--accent); font-size: 1.8rem;">${data.name}</h2>
                <p style="color: var(--text-dim);">Application No: #${data.application_no} | Status: <span class="badge badge-${data.status}">${data.status}</span></p>
            </div>

            <div class="section-title"><i class="fas fa-user-circle"></i> Personal Details</div>
            <div class="detail-grid">
                <div class="detail-item"><label>DOB</label><p>${data.dob_date}/${data.dob_month}/${data.dob_year}</p></div>
                <div class="detail-item"><label>Gender</label><p>${data.gender}</p></div>
                <div class="detail-item"><label>Email</label><p>${data.email}</p></div>
                <div class="detail-item"><label>WhatsApp</label><p>${data.whatsapp}</p></div>
                <div class="detail-item"><label>Aadhar No</label><p>${data.aadhar}</p></div>
                <div class="detail-item"><label>Blood Group</label><p>${data.blood_group}</p></div>
            </div>

            <div class="section-title"><i class="fas fa-home"></i> Family & Address</div>
            <div class="detail-grid">
                <div class="detail-item"><label>Parent Name</label><p>${data.parent_name}</p></div>
                <div class="detail-item"><label>Occupation</label><p>${data.occupation}</p></div>
                <div class="detail-item"><label>Annual Income</label><p>₹${data.annual_income}</p></div>
                <div class="detail-item"><label>Taluk</label><p>${data.taluk}</p></div>
                <div class="detail-item"><label>District</label><p>${data.district}</p></div>
                <div class="detail-item"><label>PIN Code</label><p>${data.pin_code}</p></div>
            </div>

            <div class="section-title"><i class="fas fa-graduation-cap"></i> Academic Details</div>
            <div class="detail-grid">
                <div class="detail-item"><label>Board/Univ</label><p>${data.qual_exam_board}</p></div>
                <div class="detail-item"><label>Reg No</label><p>${data.qual_exam_reg_no}</p></div>
                <div class="detail-item"><label>Percentage</label><p>${data.qual_exam_percentage}%</p></div>
                <div class="detail-item"><label>Marks</label><p>${data.qual_exam_marks_obtained} / ${data.qual_exam_max_marks}</p></div>
            </div>

            <div class="section-title"><i class="fas fa-file-alt"></i> Documents Checklist</div>
            <div style="color: var(--text-dim); display: flex; flex-wrap: wrap; gap: 10px;">
                ${data.submitted_documents ? data.submitted_documents.split(',').map(doc => `
                    <span style="background: rgba(255,255,255,0.05); padding: 5px 15px; border-radius: 12px; border: 1px solid var(--glass-border);">
                        <i class="fas fa-check-circle" style="color: var(--success); margin-right: 5px;"></i> ${doc.trim()}
                    </span>
                `).join('') : '<p>No documents submitted.</p>'}
            </div>
        `;

    } catch (err) {
        content.innerHTML = `
            <div style="text-align: center; color: var(--danger); padding: 2rem;">
                <i class="fas fa-exclamation-triangle fa-3x" style="margin-bottom: 1rem;"></i>
                <p>Failed to load profile. Error: ${err.message}</p>
            </div>
        `;
    }
}

function closeStudentModal() {
    const modal = document.getElementById('studentDetailModal');
    modal.classList.remove('active');
}

// Close on background click
window.onclick = function(event) {
    const modal = document.getElementById('studentDetailModal');
    if (event.target == modal) {
        closeStudentModal();
    }
}
