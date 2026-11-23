(function () {
  var root = document.documentElement;

  // theme toggle
  document.querySelectorAll('[data-theme-toggle]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-bs-theme', next);
      try { localStorage.setItem('theme', next); } catch (e) {}
      window.dispatchEvent(new CustomEvent('themechange', { detail: next }));
    });
  });

  // mobile sidebar
  var sidebar = document.getElementById('sidebar');
  var overlay = document.getElementById('sidebarOverlay');
  var toggle = document.getElementById('sidebarToggle');
  function setSidebar(open) {
    if (!sidebar) return;
    sidebar.classList.toggle('open', open);
    document.body.classList.toggle('sidebar-open', open);
  }
  if (toggle) toggle.addEventListener('click', function () { setSidebar(!sidebar.classList.contains('open')); });
  if (overlay) overlay.addEventListener('click', function () { setSidebar(false); });

  // auto-dismiss flash messages
  document.querySelectorAll('.alert[data-autodismiss]').forEach(function (el) {
    setTimeout(function () {
      if (window.bootstrap) { bootstrap.Alert.getOrCreateInstance(el).close(); } else { el.remove(); }
    }, 5000);
  });

  // tooltips
  if (window.bootstrap) {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) { new bootstrap.Tooltip(el); });
  }

  // confirm before destructive actions
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!window.confirm(form.getAttribute('data-confirm'))) e.preventDefault();
    });
  });
})();
