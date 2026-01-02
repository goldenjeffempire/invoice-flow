/**
 * Responsive Navigation and Sidebar Controller
 * Handles off-canvas sidebar, mobile menu toggles, and backdrop interactions.
 */
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.querySelector('[data-sidebar]');
    const overlay = document.getElementById('sidebar-overlay');
    const mobileToggle = document.getElementById('mobile-menu-toggle');
    const closeMobile = document.getElementById('sidebar-close-mobile');

    if (!sidebar || !overlay || !mobileToggle) return;

    /**
     * Toggles the sidebar visibility
     * @param {boolean} show - Whether to show or hide the sidebar
     */
    const toggleSidebar = (show) => {
        const isCollapsed = sidebar.classList.contains('collapsed');
        const shouldShow = typeof show === 'boolean' ? show : isCollapsed;

        if (shouldShow) {
            sidebar.classList.remove('collapsed');
            overlay.classList.add('is-visible');
            document.body.style.overflow = 'hidden';
            // Set focus to the first focusable element for accessibility
            const firstLink = sidebar.querySelector('.sidebar-link');
            if (firstLink) firstLink.focus();
        } else {
            sidebar.classList.add('collapsed');
            overlay.classList.remove('is-visible');
            document.body.style.overflow = '';
        }
        
        mobileToggle.setAttribute('aria-expanded', shouldShow);
    };

    // Event Listeners
    mobileToggle.addEventListener('click', () => toggleSidebar(true));
    
    if (closeMobile) {
        closeMobile.addEventListener('click', () => toggleSidebar(false));
    }

    overlay.addEventListener('click', () => toggleSidebar(false));

    // Handle Escape key to close sidebar
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !sidebar.classList.contains('collapsed')) {
            toggleSidebar(false);
            mobileToggle.focus();
        }
    });

    // Close sidebar when navigating (for mobile SPA-like feel if needed)
    const sidebarLinks = sidebar.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 1024) {
                toggleSidebar(false);
            }
        });
    });

    // Handle initial state and resize
    const handleResize = () => {
        if (window.innerWidth > 1024) {
            sidebar.classList.remove('collapsed');
            overlay.classList.remove('is-visible');
            document.body.style.overflow = '';
        } else {
            sidebar.classList.add('collapsed');
        }
    };

    window.addEventListener('resize', handleResize);
    handleResize(); // Initialize on load
});
