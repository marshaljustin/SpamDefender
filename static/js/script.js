document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const scanButton = document.getElementById('scanButton');
    const refreshButton = document.getElementById('refreshButton');
    const spamTab = document.getElementById('spamTab');
    const legitimateTab = document.getElementById('legitimateTab');
    const userProfile = document.getElementById('userProfile');
    const settingsPopover = document.getElementById('settingsPopover');
    const overlay = document.getElementById('overlay');
    const closeSettings = document.getElementById('closeSettings');
    const logoutButton = document.getElementById('logout-button');
    const darkModeToggle = document.getElementById('darkModeToggle');

    // Statistics elements
    const totalEmailsEl = document.getElementById('totalEmails');
    const spamCountEl = document.getElementById('spamCount');
    const legitimateCountEl = document.getElementById('legitimateCount');
    const spamPercentageEl = document.getElementById('spamPercentage');
    const avgSpamConfidenceEl = document.getElementById('avgSpamConfidence');
    const avgLegitConfidenceEl = document.getElementById('avgLegitConfidence');

    // Email content elements
    const spamEmailContent = document.getElementById('spamEmailContent');
    const legitimateEmailContent = document.getElementById('legitimateEmailContent');

    // Base URL for API calls
    const API_BASE = window.location.origin;

    // Check login status and initialize
    checkLoginStatus();

    // Event listeners
    if (scanButton) scanButton.addEventListener('click', scanEmails);
    if (refreshButton) refreshButton.addEventListener('click', getStats);
    if (spamTab) spamTab.addEventListener('click', () => switchTab('spam'));
    if (legitimateTab) legitimateTab.addEventListener('click', () => switchTab('legitimate'));
    if (userProfile) userProfile.addEventListener('click', openSettings);
    if (closeSettings) closeSettings.addEventListener('click', closeSettingsPopover);
    if (overlay) overlay.addEventListener('click', closeAllPopovers);
    if (logoutButton) logoutButton.addEventListener('click', handleLogout);

    // Dark mode toggle
    if (darkModeToggle) {
        // Load saved theme preference
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        darkModeToggle.checked = savedTheme === 'dark';

        darkModeToggle.addEventListener('change', function() {
            const theme = this.checked ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        });
    }

    // Settings navigation
    document.querySelectorAll('.settings-nav-item').forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons
            document.querySelectorAll('.settings-nav-item').forEach(b => b.classList.remove('active'));

            // Hide all sections
            document.querySelectorAll('.settings-main > div').forEach(section => {
                section.classList.add('hidden');
            });

            // Add active class to clicked button
            button.classList.add('active');

            // Show corresponding section
            const sections = {
                'Account': '.account-section',
                'History': '.history-section',
                'Response': '.appearance-section',
                'Data Controls': '.data-controls-section'
            };

            const sectionClass = sections[button.querySelector('span').textContent];
            if (sectionClass) {
                document.querySelector(sectionClass).classList.remove('hidden');
            }
        });
    });

    // Toggle functionality for switches
    document.querySelectorAll('.switch input').forEach(switchInput => {
        switchInput.addEventListener('change', function() {
            this.parentNode.classList.toggle('active', this.checked);
        });
    });

    // Initial load
    getStats();

    // Function to switch between tabs
    function switchTab(tab) {
        if (tab === 'spam') {
            spamTab.classList.add('active');
            legitimateTab.classList.remove('active');
            document.getElementById('spamEmails').classList.add('active');
            document.getElementById('legitimateEmails').classList.remove('active');
            getEmails('spam');
        } else {
            spamTab.classList.remove('active');
            legitimateTab.classList.add('active');
            document.getElementById('spamEmails').classList.remove('active');
            document.getElementById('legitimateEmails').classList.add('active');
            getEmails('legitimate');
        }
    }

    // Function to show loading overlay
    function showLoading() {
        document.getElementById('loader').style.display = 'flex';
    }

    // Function to hide loading overlay
    function hideLoading() {
        document.getElementById('loader').style.display = 'none';
    }

    // Function to show message
    function showMessage(message, type = 'info') {
        // Create a notification
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span>${message}</span>
                <button class="close-btn">&times;</button>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto-hide after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);

        // Close button functionality
        notification.querySelector('.close-btn').addEventListener('click', () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
    }

    // Function to handle API responses with proper error handling
    async function handleApiResponse(response) {
        const contentType = response.headers.get('content-type');
        let data;

        // Check if response is JSON
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            throw new Error(`Server returned non-JSON response: ${text.substring(0, 200)}...`);
        }

        if (!response.ok) {
            throw new Error(data.detail || data.error || data.message || `HTTP ${response.status}: ${response.statusText}`);
        }

        return data;
    }

    // Function to scan emails
    async function scanEmails() {
        showLoading();
        try {
            const response = await fetch(`${API_BASE}/api/scan-emails`, {
                method: 'POST',
                credentials: 'include' // Important for cookies
            });

            const result = await handleApiResponse(response);

            showMessage(`Successfully scanned ${result.total_emails} emails. Found ${result.spam_count} spam emails.`, 'success');

            // Refresh stats and email lists
            await getStats();
            await getEmails('spam');
            await getEmails('legitimate');

        } catch (error) {
            console.error('Error scanning emails:', error);
            showMessage(`Error scanning emails: ${error.message}`, 'error');
        } finally {
            hideLoading();
        }
    }

    // Function to get statistics
    async function getStats() {
        try {
            const response = await fetch(`${API_BASE}/api/stats`, {
                credentials: 'include' // Important for cookies
            });

            // Check if response is OK before trying to parse as JSON
            if (response.status === 404) {
                // No content - initialize with zeros
                totalEmailsEl.textContent = '0';
                spamCountEl.textContent = '0';
                legitimateCountEl.textContent = '0';
                spamPercentageEl.textContent = '0.00%';
                avgSpamConfidenceEl.textContent = '0.00%';
                avgLegitConfidenceEl.textContent = '0.00%';
                return;
            }

            const stats = await handleApiResponse(response);

            // Update statistics display
            totalEmailsEl.textContent = stats.total_emails || 0;
            spamCountEl.textContent = stats.spam_count || 0;
            legitimateCountEl.textContent = stats.legitimate_count || 0;
            spamPercentageEl.textContent = (stats.spam_percentage || 0).toFixed(2) + '%';
            avgSpamConfidenceEl.textContent = ((stats.avg_spam_confidence || 0) * 100).toFixed(2) + '%';
            avgLegitConfidenceEl.textContent = ((stats.avg_legit_confidence || 0) * 100).toFixed(2) + '%';

        } catch (error) {
            console.error('Error fetching statistics:', error);
            showMessage(`Error fetching statistics: ${error.message}`, 'error');
        }
    }

    // Function to get emails by type (spam or legitimate)
    async function getEmails(type) {
        try {
            const response = await fetch(`${API_BASE}/api/emails/${type}`, {
                credentials: 'include' // Important for cookies
            });

            // Handle case where there might be no emails
            if (response.status === 404) {
                const emailContent = type === 'spam' ? spamEmailContent : legitimateEmailContent;
                emailContent.innerHTML = '<div class="loading">No emails found</div>';
                return;
            }

            const data = await handleApiResponse(response);

            const emailContent = type === 'spam' ? spamEmailContent : legitimateEmailContent;

            // Clear previous content
            emailContent.innerHTML = '';

            if (!data.emails || data.emails.length === 0) {
                emailContent.innerHTML = '<div class="loading">No emails found</div>';
                return;
            }

            // Create email items
            data.emails.forEach(email => {
                const emailItem = document.createElement('div');
                emailItem.className = 'email-item';

                emailItem.innerHTML = `
                    <div class="email-header">
                        <div class="email-sender">${escapeHtml(email.sender)}</div>
                        <div class="email-date">${escapeHtml(email.date)}</div>
                    </div>
                    <div class="email-subject">${escapeHtml(email.subject)}</div>
                    <div class="email-preview">${escapeHtml(email.preview || (email.content ? email.content.substring(0, 100) + '...' : 'No content'))}</div>
                    <div class="email-confidence ${type === 'spam' ? 'spam-confidence' : 'legit-confidence'}">
                        Confidence: ${((email.confidence || 0) * 100).toFixed(2)}%
                    </div>
                `;

                emailContent.appendChild(emailItem);
            });

        } catch (error) {
            console.error(`Error fetching ${type} emails:`, error);
            const emailContent = type === 'spam' ? spamEmailContent : legitimateEmailContent;
            emailContent.innerHTML = `<div class="loading">Error loading emails: ${error.message}</div>`;
        }
    }

    // Helper function to escape HTML
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Settings functions
    function openSettings() {
        settingsPopover.classList.add('active');
        overlay.classList.add('active');
    }

    function closeSettingsPopover() {
        settingsPopover.classList.remove('active');
        overlay.classList.remove('active');
    }

    function closeAllPopovers() {
        closeSettingsPopover();
        overlay.classList.remove('active');
    }

    // Auth Functions
    async function handleLogout() {
    showLoading();
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });

        if (response.ok) {
            window.location.href = '/login'; // FIXED: Remove .html
        } else {
            throw new Error(`Logout failed with status: ${response.status}`);
        }
    } catch (err) {
        console.error('Logout failed:', err);
        hideLoading();
        showMessage('Logout failed. Please try again.', 'error');
    }
}

async function checkLoginStatus() {
    try {
        const response = await fetch('/api/auth/me', {
            method: 'GET',
            credentials: 'include'
        });

        if (!response.ok) {
            window.location.href = '/login'; // FIXED: Remove .html
            return;
        }

        const userData = await response.json();
        document.getElementById('userEmail').textContent = userData.email;

    } catch (err) {
        console.error('Error checking login status:', err);
        window.location.href = '/login'; // FIXED: Remove .html
    }
}
});