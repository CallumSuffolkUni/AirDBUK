function showSection(section) {
    const loginSection = document.getElementById('login-section');
    const registerSection = document.getElementById('register-section');

    // Guard: if these sections don't exist (e.g. user is logged in), do nothing
    if (!loginSection || !registerSection) return;

    loginSection.style.display = section === 'login' ? 'block' : 'none';
    registerSection.style.display = section === 'register' ? 'block' : 'none';

    loginSection.querySelectorAll('input, select, textarea').forEach(el => {
        el.disabled = section !== 'login';
    });
    registerSection.querySelectorAll('input, select, textarea').forEach(el => {
        el.disabled = section !== 'register';
    });

    document.getElementById('action-field').value = section;

    document.getElementById('login-section-btn').style.display = section === 'login' ? 'block' : 'none';
    document.getElementById('register-section-btn').style.display = section === 'register' ? 'block' : 'none';
}

// Only run if the sections exist (i.e. user is not logged in)
if (document.getElementById('login-section')) {
    showSection('login');
}