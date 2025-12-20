// Payment flow management
document.addEventListener('DOMContentLoaded', function() {
    // Handle payment button clicks
    const paymentForm = document.querySelector('form[action*="/pay/"]');
    if (paymentForm) {
        paymentForm.addEventListener('submit', function(e) {
            const button = this.querySelector('button[type="submit"]');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 24px; height: 24px; animation: spin 1s linear infinite;"><circle cx="12" cy="12" r="10"/></svg> Processing...';
            }
        });
    }
    
    // Add CSS animation for spinning
    const style = document.createElement('style');
    style.textContent = `
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
});
