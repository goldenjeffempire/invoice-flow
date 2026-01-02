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
     */
    const toggleSidebar = (show) => {
        const isCollapsed = sidebar.classList.contains('collapsed');
        const shouldShow = typeof show === 'boolean' ? show : isCollapsed;

        if (shouldShow) {
            sidebar.classList.remove('collapsed');
            overlay.classList.add('is-visible');
            document.body.style.overflow = 'hidden';
            const firstLink = sidebar.querySelector('.sidebar-link');
            if (firstLink) firstLink.focus();
        } else {
            sidebar.classList.add('collapsed');
            overlay.classList.remove('is-visible');
            document.body.style.overflow = '';
        }
        
        mobileToggle.setAttribute('aria-expanded', shouldShow);
    };

    // Mobile Toggle Listeners
    mobileToggle.addEventListener('click', () => toggleSidebar(true));
    if (closeMobile) closeMobile.addEventListener('click', () => toggleSidebar(false));
    overlay.addEventListener('click', () => toggleSidebar(false));

    // Collapsible Sections
    const sectionToggles = document.querySelectorAll('.sidebar-section-toggle');
    sectionToggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
            const targetId = toggle.getAttribute('aria-controls');
            const targetList = document.getElementById(targetId);
            
            toggle.setAttribute('aria-expanded', !isExpanded);
            if (targetList) {
                targetList.style.maxHeight = isExpanded ? '0' : targetList.scrollHeight + 'px';
                targetList.setAttribute('aria-hidden', isExpanded);
            }
        });
        
        // Initialize state
        const targetId = toggle.getAttribute('aria-controls');
        const targetList = document.getElementById(targetId);
        if (targetList && toggle.getAttribute('aria-expanded') === 'true') {
            targetList.style.maxHeight = targetList.scrollHeight + 'px';
        }
    });

    // Keyboard Accessibility
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !sidebar.classList.contains('collapsed')) {
            toggleSidebar(false);
            mobileToggle.focus();
        }
    });

    const sidebarLinks = sidebar.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (window.innerWidth <= 1024) toggleSidebar(false);
        });
    });

    // Handle Resize
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
    handleResize();
});
