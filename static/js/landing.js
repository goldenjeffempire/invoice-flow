document.addEventListener('DOMContentLoaded', () => {
    // Reveal Observer
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.reveal-on-scroll').forEach(el => revealObserver.observe(el));

    // Intro Slides Logic
    const intro = document.getElementById('intro-slides');
    const slides = document.querySelectorAll('.slide');
    const nextButtons = document.querySelectorAll('.next-slide');
    let currentSlide = 0;

    if (localStorage.getItem('saas_landing_seen')) {
        if (intro) intro.style.display = 'none';
    } else {
        nextButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                slides[currentSlide].style.opacity = '0';
                slides[currentSlide].style.transform = 'translateY(-20px)';
                
                setTimeout(() => {
                    slides[currentSlide].classList.remove('active');
                    currentSlide++;
                    
                    if (currentSlide < slides.length) {
                        slides[currentSlide].classList.add('active');
                    } else {
                        intro.style.opacity = '0';
                        intro.style.filter = 'blur(20px)';
                        setTimeout(() => {
                            intro.style.display = 'none';
                            localStorage.setItem('saas_landing_seen', 'true');
                            // Trigger first reveal manually after intro
                            document.querySelector('.hero .reveal-on-scroll').classList.add('active');
                        }, 800);
                    }
                }, 400);
            });
        });
    }

    // Dynamic FAQ Loader
    const faqBox = document.getElementById('faq-container');
    if (faqBox) {
        fetch('/static/data/faq.json')
            .then(r => r.json())
            .then(data => {
                faqBox.innerHTML = data.faq.map((item, idx) => `
                    <div class="faq-item reveal-on-scroll" style="transition-delay: ${idx * 0.1}s">
                        <h4 class="text-xl font-bold mb-3 text-gray-900">${item.question}</h4>
                        <p class="text-gray-600 leading-relaxed">${item.answer}</p>
                    </div>
                `).join('');
                document.querySelectorAll('#faq-container .reveal-on-scroll').forEach(el => revealObserver.observe(el));
            })
            .catch(() => {
                faqBox.innerHTML = '<div class="p-6 bg-red-50 text-red-600 rounded-2xl">Unable to sync FAQs. Please refresh.</div>';
            });
    }

    // Smooth Navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const offset = 80;
                const bodyRect = document.body.getBoundingClientRect().top;
                const elementRect = target.getBoundingClientRect().top;
                const elementPosition = elementRect - bodyRect;
                const offsetPosition = elementPosition - offset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
});
