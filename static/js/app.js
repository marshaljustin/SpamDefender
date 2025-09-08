document.addEventListener('DOMContentLoaded', () => {
    const showError = (message) => {
      const errorEl = document.getElementById('errorMessage');
      errorEl.textContent = message;
      errorEl.style.display = 'block';
      setTimeout(() => errorEl.style.display = 'none', 5000);
    };

    const showSuccess = (message) => {
      const successEl = document.getElementById('successMessage');
      if (successEl) {
        successEl.textContent = message;
        successEl.style.display = 'block';
        setTimeout(() => successEl.style.display = 'none', 5000);
      }
    };

    const setButtonsDisabled = (disabled) => {
      const googleBtn = document.getElementById('googleBtn');
      const submitBtn = document.querySelector('button[type="submit"]');

      if (googleBtn) googleBtn.disabled = disabled;
      if (submitBtn) submitBtn.disabled = disabled;
    };

    // Check for URL parameters (from OAuth callback)
    const checkUrlParams = () => {
      const urlParams = new URLSearchParams(window.location.search);
      const error = urlParams.get('error');
      const success = urlParams.get('success');

      if (error) {
        showError(decodeURIComponent(error));
      } else if (success) {
        showSuccess(decodeURIComponent(success));
      }

      // Clean up URL parameters
      if (error || success) {
        const cleanUrl = window.location.origin + window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
      }
    };

    // Google Login Handler
    if (document.getElementById('googleBtn')) {
  document.getElementById('googleBtn').addEventListener('click', async (e) => {
    e.preventDefault();

    try {
      showLoader();
      setButtonsDisabled(true);

      // Store the current page as redirect target after login
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && currentPath !== '/register') {
        document.cookie = `redirect_after_login=${currentPath}; path=/; max-age=300`; // 5 minutes
      }

      // Small delay to show loading state
      await new Promise(resolve => setTimeout(resolve, 500));

      // Redirect to Google OAuth endpoint
      window.location.href = '/api/auth/google';
    } catch (error) {
      hideLoader();
      setButtonsDisabled(false);
      showError('Failed to initiate Google login. Please try again.');
      console.error('Google login error:', error);
    }
  });
}

    // Registration Handler
    hideLoader();

    if (document.getElementById('registerForm')) {
      document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        showLoader();
        try {
          btn.disabled = true;
          btn.textContent = 'Registering...';
          setButtonsDisabled(true);

          await new Promise(resolve => setTimeout(resolve, 500));

          const formData = {
            email: document.getElementById('email').value,
            password: document.getElementById('password').value
          };

          const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(formData)
          });

          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.detail || data.message || 'Registration failed');
          }

          hideLoader();
          await new Promise(resolve => setTimeout(resolve, 100));
          window.location.href = '/index'; // FIXED: Remove .html

        } catch (err) {
          showError(err.message);
        } finally {
          btn.disabled = false;
          btn.textContent = 'Sign up';
          setButtonsDisabled(false);
          hideLoader();
        }
      });
    }

    // Login Handler
    hideLoader();
    if (document.getElementById('loginForm')) {
      document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button');
        showLoader();
        try {
          btn.disabled = true;
          btn.textContent = 'Signing in...';
          setButtonsDisabled(true);

          await new Promise(resolve => setTimeout(resolve, 500));

          const email = document.getElementById('email').value.trim();
          const password = document.getElementById('password').value;

          // Client-side validation
          if (!email || !password) {
            throw new Error('Please enter both email and password.');
          }

          // Basic email validation
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
          if (!emailRegex.test(email)) {
            throw new Error('Please enter a valid email address.');
          }

          if (password.length < 6) {
            throw new Error('Password must be at least 6 characters long.');
          }

          const formData = {
            email: email,
            password: password
          };

          const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(formData)
          });

          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.detail || data.message || 'Login failed');
          }

          showSuccess('Login successful! Redirecting...');
          setTimeout(() => {
            window.location.href = data.redirect_url || '/index';
          }, 1500);

        } catch (err) {
          showError(err.message);
        } finally {
          btn.disabled = false;
          btn.textContent = 'Sign in';
          setButtonsDisabled(false);
          hideLoader();
        }
      });
    }

    // Check URL parameters on page load
    checkUrlParams();

    // Handle browser back/forward buttons
    window.addEventListener('popstate', function() {
      checkUrlParams();
    });

    // Enhanced keyboard navigation
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        const errorEl = document.getElementById('errorMessage');
        const successEl = document.getElementById('successMessage');

        if (errorEl) errorEl.style.display = 'none';
        if (successEl) successEl.style.display = 'none';
        hideLoader();
      }
    });

    // Auto-focus email field on login/register pages
    const emailInput = document.getElementById('email');
    if (emailInput) {
      emailInput.focus();
    }
  });

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
      const userEmailEl = document.getElementById('userEmail');
      if (userEmailEl) {
        userEmailEl.textContent = userData.email;
      }

      window.history.replaceState({}, document.title, window.location.href);

    } catch (err) {
      window.location.href = '/login'; // FIXED: Remove .html
    }
  }

  window.onpageshow = function(event) {
    if (event.persisted) {
      checkLoginStatus();
    }
  };

  function showLoader() {
    const loaderEl = document.getElementById("loader");
    if (loaderEl) {
      loaderEl.style.display = "flex";
      loaderEl.classList.add('show');
    }
    document.body.classList.add('modal-open');
  }

  function hideLoader() {
    const loaderEl = document.getElementById("loader");
    if (loaderEl) {
      loaderEl.style.display = "none";
      loaderEl.classList.remove('show');
    }
    document.body.classList.remove('modal-open');
  }

  // Logout function (if needed for other pages)
  async function logout() {
    try {
      showLoader();
      const response = await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include'
      });

      if (response.ok) {
        window.location.href = '/login';
      } else {
        throw new Error('Logout failed');
      }
    } catch (err) {
      console.error('Logout error:', err);
      // Force redirect even if logout endpoint fails
      window.location.href = '/login';
    } finally {
      hideLoader();
    }
  }

  // Make logout function available globally
  window.logout = logout;
