// static/js/session-timeout.js
// Session timeout warning and auto-logout

let timeoutWarningTimer;
let logoutTimer;
let warningModal;

// Session timeout settings (in milliseconds)
const SESSION_TIMEOUT = {{ session_timeout_seconds|default:1800 }} * 1000; // 30 minutes
const WARNING_BEFORE = 60000; // Show warning 1 minute before logout

// Initialize session monitoring
function initSessionTimeout() {
    if (typeof sessionTimeoutSeconds === 'undefined') {
        // Get from meta tag if available
        const meta = document.querySelector('meta[name="session-timeout"]');
        if (meta) {
            SESSION_TIMEOUT = parseInt(meta.content) * 1000;
        }
    }
    
    resetTimers();
    startActivityMonitoring();
}

// Reset timers on user activity
function resetTimers() {
    clearTimeout(timeoutWarningTimer);
    clearTimeout(logoutTimer);
    
    // Set timer to show warning
    timeoutWarningTimer = setTimeout(showWarningModal, SESSION_TIMEOUT - WARNING_BEFORE);
    
    // Set timer to logout
    logoutTimer = setTimeout(forceLogout, SESSION_TIMEOUT);
}

// Show warning modal to user
function showWarningModal() {
    // Create modal if not exists
    if (!document.getElementById('sessionWarningModal')) {
        createWarningModal();
    }
    
    // Show modal
    const modal = document.getElementById('sessionWarningModal');
    modal.style.display = 'flex';
    
    // Countdown timer
    let remainingSeconds = Math.floor(WARNING_BEFORE / 1000);
    const countdownElement = document.getElementById('sessionCountdown');
    
    const countdownInterval = setInterval(() => {
        remainingSeconds--;
        if (countdownElement) {
            const minutes = Math.floor(remainingSeconds / 60);
            const seconds = remainingSeconds % 60;
            countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
        
        if (remainingSeconds <= 0) {
            clearInterval(countdownInterval);
        }
    }, 1000);
}

// Create warning modal dynamically
function createWarningModal() {
    const modalHtml = `
        <div id="sessionWarningModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 9999; align-items: center; justify-content: center;">
            <div style="background: white; border-radius: 12px; max-width: 400px; width: 90%; padding: 24px; text-align: center; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);">
                <div style="font-size: 48px; margin-bottom: 16px;">⏰</div>
                <h3 style="font-size: 20px; font-weight: bold; margin-bottom: 12px;">Session Timeout Warning</h3>
                <p style="color: #666; margin-bottom: 16px;">Your session will expire in <span id="sessionCountdown" style="font-weight: bold; color: #e74c3c;">1:00</span> due to inactivity.</p>
                <p style="color: #666; margin-bottom: 24px;">Click "Stay Logged In" to continue your session.</p>
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <button onclick="stayLoggedIn()" style="background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer;">Stay Logged In</button>
                    <button onclick="forceLogout()" style="background: #e74c3c; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer;">Logout Now</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// Keep user logged in
function stayLoggedIn() {
    // Close modal
    const modal = document.getElementById('sessionWarningModal');
    if (modal) modal.style.display = 'none';
    
    // Send keep-alive request to server
    fetch('/api/keep-alive/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json'
        }
    }).then(response => {
        if (response.ok) {
            resetTimers();
        } else {
            forceLogout();
        }
    }).catch(() => {
        forceLogout();
    });
}

// Force logout
function forceLogout() {
    // Clear all timers
    clearTimeout(timeoutWarningTimer);
    clearTimeout(logoutTimer);
    
    // Send logout request
    fetch('/users/logout/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json'
        }
    }).finally(() => {
        window.location.href = '/users/login/?timeout=true';
    });
}

// Monitor user activity
function startActivityMonitoring() {
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
    
    events.forEach(event => {
        document.addEventListener(event, () => {
            resetTimers();
            
            // Also send keep-alive to server occasionally
            const lastKeepAlive = localStorage.getItem('lastKeepAlive') || 0;
            const now = Date.now();
            
            if (now - lastKeepAlive > 60000) { // Every minute
                localStorage.setItem('lastKeepAlive', now);
                fetch('/api/keep-alive/', {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                        'Content-Type': 'application/json'
                    }
                }).catch(error => console.error('Keep-alive failed:', error));
            }
        });
    });
}

// Get CSRF token from cookies
function getCsrfToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [key, value] = cookie.trim().split('=');
        if (key === name) return value;
    }
    return '';
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSessionTimeout);
} else {
    initSessionTimeout();
}