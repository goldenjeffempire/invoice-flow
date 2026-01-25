document.addEventListener('DOMContentLoaded', () => {
    // Intro Slides Logic
    const intro = document.getElementById('intro-slides');
    const slides = document.querySelectorAll('.slide');
    const nextButtons = document.querySelectorAll('.next-slide');
    let currentSlide = 0;

    const skipIntro = () => {
        intro.style.opacity = '0';
        intro.style.visibility = 'hidden';
        localStorage.setItem('premium_landing_intro_seen', 'true');
        setTimeout(() => intro.remove(), 800);
    };

    if (localStorage.getItem('premium_landing_intro_seen')) {
        intro.style.display = 'none';
    } else {
        nextButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                slides[currentSlide].classList.remove('active');
                currentSlide++;
                if (currentSlide < slides.length) {
                    slides[currentSlide].classList.add('active');
                } else {
                    skipIntro();
                }
            });
        });
    }

    // Scroll Reveal
    const observerOptions = {
        threshold: 0.15,
        rootMargin: '0px 0px -100px 0px'
    };

    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                revealObserver.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

    // Dynamic FAQ
    const faqContainer = document.getElementById('faq-container');
    if (faqContainer) {
        fetch('/static/data/faq.json')
            .then(res => res.json())
            .then(data => {
                faqContainer.innerHTML = data.faq.map((item, index) => `
                    <div class="faq-item reveal" style="transition-delay: ${index * 0.1}s">
                        <div class="faq-question">
                            <span>${item.question}</span>
                            <svg class="w-6 h-6 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        </div>
                        <div class="faq-answer">
                            <p>${item.answer}</p>
                        </div>
                    </div>
                `).join('');

                document.querySelectorAll('.faq-question').forEach(q => {
                    q.addEventListener('click', () => {
                        const item = q.parentElement;
                        item.classList.toggle('active');
                        q.querySelector('svg').classList.toggle('rotate-180');
                    });
                });

                document.querySelectorAll('#faq-container .reveal').forEach(el => revealObserver.observe(el));
            })
            .catch(() => {
                faqContainer.innerHTML = '<div class="text-center p-8 bg-red-50 text-red-600 rounded-3xl">Failed to sync FAQ engine.</div>';
            });
    }

    // Smooth Scroll
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const navHeight = document.querySelector('nav').offsetHeight;
                window.scrollTo({
                    top: target.offsetTop - navHeight,
                    behavior: 'smooth'
                });
            }
        });
    });
});
