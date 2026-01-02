/**
 * Responsive Navigation and Sidebar Interactions
 */
document.addEventListener('DOMContentLoaded', () => {
    const layout = document.getElementById('app-layout');
    const sidebar = document.querySelector('[data-sidebar]');
    const toggleBtn = document.getElementById('sidebar-toggle');
    const closeMobileBtn = document.getElementById('sidebar-close-mobile');
    const overlay = document.getElementById('sidebar-overlay');

    if (!layout || !sidebar) return;

    // Load initial state
    const isCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
    if (isCollapsed && window.innerWidth > 1024) {
        layout.classList.add('sidebar-collapsed');
    }

    function toggleSidebar() {
        if (window.innerWidth <= 1024) {
            // Mobile: Toggle visibility
            sidebar.classList.toggle('is-open');
            if (overlay) overlay.classList.toggle('is-visible');
            document.body.style.overflow = sidebar.classList.contains('is-open') ? 'hidden' : '';
            
            // Focus management for mobile
            if (sidebar.classList.contains('is-open')) {
                const firstLink = sidebar.querySelector('.sidebar-link');
                if (firstLink) firstLink.focus();
            }
        } else {
            // Desktop: Toggle collapsed state
            layout.classList.toggle('sidebar-collapsed');
            localStorage.setItem('sidebar-collapsed', layout.classList.contains('sidebar-collapsed'));
        }
    }

    function closeSidebar() {
        sidebar.classList.remove('is-open');
        if (overlay) overlay.classList.remove('is-visible');
        document.body.style.overflow = '';
    }

    if (toggleBtn) toggleBtn.addEventListener('click', toggleSidebar);
    if (closeMobileBtn) closeMobileBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);

    // Handle resize
    window.addEventListener('resize', () => {
        if (window.innerWidth > 1024) {
            closeSidebar();
        }
    });

    // Handle escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
            closeSidebar();
        }
    });
});
