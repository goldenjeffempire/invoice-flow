(function() {
    const sidebar = document.querySelector('[data-sidebar]');
    const mobileToggle = document.getElementById('mobile-menu-toggle');
    const overlay = document.getElementById('sidebar-overlay');
    const closeMobile = document.getElementById('sidebar-close-mobile');

    if (!sidebar) return;

    function toggleSidebar() {
        const isOpen = sidebar.classList.toggle('is-open');
        if (overlay) overlay.classList.toggle('is-visible', isOpen);
        document.body.style.overflow = isOpen ? 'hidden' : '';
    }

    if (mobileToggle) mobileToggle.addEventListener('click', toggleSidebar);
    if (overlay) overlay.addEventListener('click', toggleSidebar);
    if (closeMobile) closeMobile.addEventListener('click', toggleSidebar);

    // Keyboard navigation for accessibility
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
            toggleSidebar();
        }
    });

    // Handle responsiveness on resize
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 1024 && sidebar.classList.contains('is-open')) {
            sidebar.classList.remove('is-open');
            if (overlay) overlay.classList.remove('is-visible');
            document.body.style.overflow = '';
        }
    });
})();