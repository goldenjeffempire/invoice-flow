/**
 * Interactive Components Library
 * Handles dropdowns, modals, tooltips, and other interactive elements
 */

(function() {
    'use strict';

    const InteractiveComponents = {
        init: function() {
            this.setupDropdowns();
            this.setupCollapsibles();
            this.setupToasts();
            this.setupModals();
        },

        // Dropdown Menu Management
        setupDropdowns: function() {
            const triggers = document.querySelectorAll('.dropdown-trigger');
            
            triggers.forEach(trigger => {
                const btn = trigger.querySelector('[data-dropdown-toggle]');
                if (!btn) return;

                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleDropdown(trigger);
                });
            });

            // Close dropdowns when clicking outside
            document.addEventListener('click', (e) => {
                triggers.forEach(trigger => {
                    if (!trigger.contains(e.target)) {
                        trigger.classList.remove('active');
                    }
                });
            });
        },

        toggleDropdown: function(trigger) {
            const isActive = trigger.classList.contains('active');
            
            // Close all other dropdowns
            document.querySelectorAll('.dropdown-trigger.active').forEach(el => {
                if (el !== trigger) {
                    el.classList.remove('active');
                }
            });

            // Toggle current dropdown
            if (isActive) {
                trigger.classList.remove('active');
            } else {
                trigger.classList.add('active');
            }
        },

        // Collapsible Sections
        setupCollapsibles: function() {
            const sections = document.querySelectorAll('[data-collapsible]');
            
            sections.forEach(section => {
                const header = section.querySelector('.collapsible-header');
                if (!header) return;

                header.addEventListener('click', () => {
                    section.classList.toggle('active');
                });
            });
        },

        // Toast Notifications
        setupToasts: function() {
            window.showToast = (message, type = 'info', duration = 4000) => {
                const toast = document.createElement('div');
                toast.className = `toast ${type}`;
                toast.innerHTML = `
                    <div class="toast-title">${type.charAt(0).toUpperCase() + type.slice(1)}</div>
                    <div class="toast-message">${message}</div>
                    <button class="toast-close" aria-label="Close">&times;</button>
                `;

                document.body.appendChild(toast);

                const closeBtn = toast.querySelector('.toast-close');
                const removeToast = () => toast.remove();

                closeBtn.addEventListener('click', removeToast);
                setTimeout(removeToast, duration);
            };
        },

        // Modal Handling
        setupModals: function() {
            const modalTriggers = document.querySelectorAll('[data-modal-toggle]');
            
            modalTriggers.forEach(trigger => {
                trigger.addEventListener('click', (e) => {
                    e.preventDefault();
                    const modalId = trigger.getAttribute('data-modal-toggle');
                    const modal = document.getElementById(modalId);
                    if (modal) {
                        modal.classList.add('active');
                        this.setupModalClose(modal);
                    }
                });
            });
        },

        setupModalClose: function(modal) {
            const closeBtn = modal.querySelector('[data-modal-close]');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    modal.classList.remove('active');
                });
            }

            // Close on backdrop click
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.remove('active');
                }
            });

            // Close on Escape key
            const escapeHandler = (e) => {
                if (e.key === 'Escape') {
                    modal.classList.remove('active');
                    document.removeEventListener('keydown', escapeHandler);
                }
            };
            document.addEventListener('keydown', escapeHandler);
        },

        // Tab Management
        setupTabs: function() {
            const tabGroups = document.querySelectorAll('[data-tabs]');
            
            tabGroups.forEach(group => {
                const tabs = group.querySelectorAll('[data-tab]');
                const panels = group.querySelectorAll('[data-panel]');

                tabs.forEach(tab => {
                    tab.addEventListener('click', (e) => {
                        e.preventDefault();
                        const panelId = tab.getAttribute('data-tab');

                        // Remove active class from all tabs and panels
                        tabs.forEach(t => t.classList.remove('active'));
                        panels.forEach(p => p.classList.remove('active'));

                        // Add active class to current tab and panel
                        tab.classList.add('active');
                        const panel = group.querySelector(`[data-panel="${panelId}"]`);
                        if (panel) {
                            panel.classList.add('active');
                        }
                    });
                });
            });
        },

        // Form Validation
        validateForm: function(form) {
            let isValid = true;
            const inputs = form.querySelectorAll('[required]');

            inputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.classList.add('error');
                } else {
                    input.classList.remove('error');
                }
            });

            return isValid;
        },

        // Smooth Scroll
        smoothScroll: function(target) {
            const element = document.querySelector(target);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        },

        // Animate Counter
        animateCounter: function(element, target, duration = 2000) {
            const start = parseInt(element.textContent);
            const increment = (target - start) / (duration / 16);
            let current = start;

            const timer = setInterval(() => {
                current += increment;
                if (current >= target) {
                    element.textContent = target.toLocaleString();
                    clearInterval(timer);
                } else {
                    element.textContent = Math.floor(current).toLocaleString();
                }
            }, 16);
        },

        // Add Loading State
        setLoading: function(element, isLoading = true) {
            if (isLoading) {
                element.disabled = true;
                element.classList.add('loading');
                element.setAttribute('aria-busy', 'true');
            } else {
                element.disabled = false;
                element.classList.remove('loading');
                element.setAttribute('aria-busy', 'false');
            }
        },

        // Copy to Clipboard
        copyToClipboard: function(text) {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(text).then(() => {
                    window.showToast('Copied to clipboard!', 'success');
                });
            } else {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                window.showToast('Copied to clipboard!', 'success');
            }
        }
    };

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            InteractiveComponents.init();
        });
    } else {
        InteractiveComponents.init();
    }

    // Export for external use
    window.InteractiveComponents = InteractiveComponents;
})();
