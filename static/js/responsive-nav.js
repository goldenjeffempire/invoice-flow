/**
 * InvoiceFlow - Responsive Navigation System
 * Handles sidebar toggle, mobile navigation, and responsive behaviors
 */

(function() {
    'use strict';

    // State
    let sidebarOpen = false;
    let mobileNavOpen = false;
    let lastScrollY = 0;

    // DOM Elements
    const sidebar = document.querySelector('.authenticated-sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const sidebarCloseMobile = document.getElementById('sidebar-close-mobile');

    // Initialize
    function init() {
        if (!sidebar) return;
        setupSidebar();
        setupKeyboardNav();
    }

    // Sidebar functionality
    function setupSidebar() {
        if (mobileMenuToggle) {
            mobileMenuToggle.addEventListener('click', toggleSidebar);
        }

        if (sidebarCloseMobile) {
            sidebarCloseMobile.addEventListener('click', closeSidebar);
        }

        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', closeSidebar);
        }

        // Close sidebar on link click (mobile)
        const sidebarLinks = sidebar.querySelectorAll('.sidebar-link');
        sidebarLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    closeSidebar();
                }
            });
        });
    }

    function toggleSidebar() {
        sidebar.classList.toggle('collapsed');
        const isOpen = !sidebar.classList.contains('collapsed');
        
        if (sidebarOverlay) {
            sidebarOverlay.classList.toggle('is-visible', isOpen);
        }
        
        document.body.style.overflow = isOpen ? 'hidden' : '';
    }

    function closeSidebar() {
        sidebar.classList.add('collapsed');
        if (sidebarOverlay) {
            sidebarOverlay.classList.remove('is-visible');
        }
        document.body.style.overflow = '';
    }

    // Mobile navigation for landing pages
    function setupMobileNav() {
        if (!navToggle || !mobileNav) return;

        navToggle.addEventListener('click', toggleMobileNav);

        // Close when clicking links
        const mobileLinks = mobileNav.querySelectorAll('.mobile-nav-link, .mobile-nav-btn');
        mobileLinks.forEach(link => {
            link.addEventListener('click', () => {
                closeMobileNav();
            });
        });
    }

    function toggleMobileNav() {
        mobileNavOpen = !mobileNavOpen;
        mobileNav.classList.toggle('is-open', mobileNavOpen);
        mobileNav.setAttribute('aria-hidden', !mobileNavOpen);
        navToggle.setAttribute('aria-expanded', mobileNavOpen);
        document.body.style.overflow = mobileNavOpen ? 'hidden' : '';
        
        if (mobileNavOpen) {
            trapFocus(mobileNav);
        }
    }

    function closeMobileNav() {
        mobileNavOpen = false;
        mobileNav.classList.remove('is-open');
        mobileNav.setAttribute('aria-hidden', 'true');
        
        if (navToggle) {
            navToggle.setAttribute('aria-expanded', 'false');
        }
        
        document.body.style.overflow = '';
    }

    // Landing page navigation scroll behavior
    function setupLandingNav() {
        if (!navLanding) return;

        window.addEventListener('scroll', () => {
            const scrollY = window.scrollY;
            
            if (scrollY > 50) {
                navLanding.classList.add('is-scrolled');
            } else {
                navLanding.classList.remove('is-scrolled');
            }
            
            lastScrollY = scrollY;
        }, { passive: true });
    }

    // Scroll behavior
    function setupScrollBehavior() {
        // Close mobile menus on scroll
        let scrollTimeout;
        window.addEventListener('scroll', () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                if (mobileNavOpen && Math.abs(window.scrollY - lastScrollY) > 100) {
                    closeMobileNav();
                }
            }, 100);
        }, { passive: true });
    }

    // Keyboard navigation
    function setupKeyboardNav() {
        document.addEventListener('keydown', (e) => {
            // Escape to close menus
            if (e.key === 'Escape') {
                if (sidebarOpen) {
                    closeSidebar();
                    mobileMenuToggle?.focus();
                }
                if (mobileNavOpen) {
                    closeMobileNav();
                    navToggle?.focus();
                }
            }
        });
    }

    // Handle window resize
    function handleResize() {
        const width = window.innerWidth;
        
        // Close mobile sidebar on larger screens
        if (width >= 768 && sidebarOpen) {
            closeSidebar();
        }
        
        // Close mobile nav on larger screens
        if (width >= 768 && mobileNavOpen) {
            closeMobileNav();
        }
    }

    // Focus trap for modals/sidebars
    function trapFocus(element) {
        const focusableElements = element.querySelectorAll(
            'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        
        if (focusableElements.length === 0) return;
        
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        
        firstElement.focus();
        
        element.addEventListener('keydown', function handleTab(e) {
            if (e.key !== 'Tab') return;
            
            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        });
    }

    // Utility: Debounce
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
