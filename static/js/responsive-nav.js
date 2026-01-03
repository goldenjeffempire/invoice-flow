/**
 * Responsive Navigation and Sidebar Interactions
 */
document.addEventListener('DOMContentLoaded', () => {
    // 1. Authenticated Sidebar Logic
    const layout = document.getElementById('app-layout');
    const sidebar = document.querySelector('[data-sidebar]');
    const toggleBtn = document.getElementById('sidebar-toggle');
    const closeMobileBtn = document.getElementById('sidebar-close-mobile');
    const overlay = document.getElementById('sidebar-overlay');

    if (layout && sidebar) {
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
                const isCollapsedNow = layout.classList.contains('sidebar-collapsed');
                localStorage.setItem('sidebar-collapsed', isCollapsedNow);
                
                // Update toggle button aria-expanded state
                if (toggleBtn) {
                    toggleBtn.setAttribute('aria-expanded', !isCollapsedNow);
                }
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

        // Handle escape key for authenticated sidebar
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && sidebar.classList.contains('is-open')) {
                closeSidebar();
            }
        });
    }

    // 2. Landing Page Navbar Toggle Logic
    const landingToggle = document.getElementById('navbar-toggle');
    const mobileNav = document.getElementById('mobile-nav');

    if (landingToggle && mobileNav) {
        landingToggle.addEventListener('click', () => {
            const isExpanded = landingToggle.getAttribute('aria-expanded') === 'true';
            landingToggle.setAttribute('aria-expanded', !isExpanded);
            landingToggle.classList.toggle('active');
            mobileNav.classList.toggle('is-open');
            mobileNav.setAttribute('aria-hidden', isExpanded);
            
            // Toggle body scroll
            document.body.style.overflow = !isExpanded ? 'hidden' : '';
        });

        // Close mobile nav when clicking a link
        const mobileLinks = mobileNav.querySelectorAll('a');
        mobileLinks.forEach(link => {
            link.addEventListener('click', () => {
                landingToggle.setAttribute('aria-expanded', 'false');
                landingToggle.classList.remove('active');
                mobileNav.classList.remove('is-open');
                mobileNav.setAttribute('aria-hidden', 'true');
                document.body.style.overflow = '';
            });
        });
    }

    // Global Resize Handler
    window.addEventListener('resize', () => {
        if (window.innerWidth > 1024) {
            // Reset Authenticated Sidebar
            if (sidebar) {
                sidebar.classList.remove('is-open');
                if (overlay) overlay.classList.remove('is-visible');
                document.body.style.overflow = '';
            }
            
            // Reset Landing Page Nav
            if (landingToggle && mobileNav) {
                landingToggle.setAttribute('aria-expanded', 'false');
                landingToggle.classList.remove('active');
                mobileNav.classList.remove('is-open');
                mobileNav.setAttribute('aria-hidden', 'true');
                document.body.style.overflow = '';
            }
        }
    });
});
