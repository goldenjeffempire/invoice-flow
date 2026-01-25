document.addEventListener('DOMContentLoaded', () => {
  const slides = document.querySelectorAll('.slide-content');
  const overlay = document.querySelector('.intro-overlay');
  let currentSlide = 0;

  if (overlay && slides.length > 0) {
    const showSlide = (index) => {
      slides.forEach(s => s.classList.remove('active'));
      if (index < slides.length) {
        slides[index].classList.add('active');
        setTimeout(() => showSlide(index + 1), 2500);
      } else {
        overlay.classList.add('dismissed');
        document.body.style.overflow = 'auto';
      }
    };

    document.body.style.overflow = 'hidden';
    showSlide(0);
  }

  // Intersection Observer for reveals
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('reveal-visible');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

  // Dynamic FAQ from JSON
  const faqData = [
    { q: "Is InvoiceFlow secure?", a: "Yes, we use industry-standard encryption and secure payment gateways like Paystack." },
    { q: "Can I cancel anytime?", a: "Absolutely. No long-term contracts, cancel your subscription at any time with one click." },
    { q: "Do you offer custom branding?", a: "Yes, our Professional and Enterprise plans allow full logo and color customization." }
  ];

  const faqContainer = document.getElementById('dynamic-faq');
  if (faqContainer) {
    faqData.forEach(item => {
      const div = document.createElement('div');
      div.className = 'reveal glass-card p-6 rounded-2xl mb-4 border border-slate-100 hover:border-blue-200 transition-all cursor-pointer group';
      div.innerHTML = `
        <h4 class="font-bold text-slate-900 flex justify-between items-center">
          ${item.q}
          <span class="text-blue-500 group-hover:rotate-90 transition-transform">+</span>
        </h4>
        <p class="mt-3 text-slate-600 hidden group-hover:block animate-fadeIn">${item.a}</p>
      `;
      faqContainer.appendChild(div);
      revealObserver.observe(div);
    });
  }
});
