/* login.js
 * Toggle show/hide password for the Arduino admin login page.
 */
(function(){
  function initToggle(){
    const pwdInput = document.getElementById('password-input');
    const toggleBtn = document.getElementById('toggle-password');
    const eyeOpen = document.getElementById('eye-open');
    const eyeClosed = document.getElementById('eye-closed');

    if (!pwdInput || !toggleBtn) return false;

    // Ensure initial icon state
    if (eyeOpen) eyeOpen.style.display = '';
    if (eyeClosed) eyeClosed.style.display = 'none';

    toggleBtn.addEventListener('click', function(){
      const type = pwdInput.getAttribute('type') === 'password' ? 'text' : 'password';
      pwdInput.setAttribute('type', type);
      if (type === 'text') {
        if (eyeOpen) eyeOpen.style.display = 'none';
        if (eyeClosed) eyeClosed.style.display = '';
        toggleBtn.setAttribute('aria-label', 'Ocultar contraseña');
        toggleBtn.setAttribute('title', 'Ocultar contraseña');
      } else {
        if (eyeOpen) eyeOpen.style.display = '';
        if (eyeClosed) eyeClosed.style.display = 'none';
        toggleBtn.setAttribute('aria-label', 'Mostrar contraseña');
        toggleBtn.setAttribute('title', 'Mostrar contraseña');
      }
    });
    return true;
  }

  // If DOM already loaded, init immediately; otherwise wait for DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initToggle);
  } else {
    // DOM already ready
    initToggle();
  }
})();
