document.addEventListener('DOMContentLoaded', () => {
    // Intro Slides Logic with Accessibility
    const intro = document.getElementById('intro-slides');
    const slides = document.querySelectorAll('.slide');
    const nextButtons = document.querySelectorAll('.next-slide');
    let currentSlide = 0;

    const updateAria = () => {
        slides.forEach((s, i) => {
            s.setAttribute('aria-hidden', i !== currentSlide);
        });
    };

    const skipIntro = () => {
        intro.style.opacity = '0';
        intro.style.visibility = 'hidden';
        localStorage.setItem('production_landing_intro_seen', 'true');
        setTimeout(() => intro.remove(), 1000);
    };

    if (localStorage.getItem('production_landing_intro_seen')) {
        if (intro) intro.remove();
    } else {
        updateAria();
        nextButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                slides[currentSlide].classList.remove('active');
                currentSlide++;
                if (currentSlide < slides.length) {
                    slides[currentSlide].classList.add('active');
                    updateAria();
                } else {
                    skipIntro();
                }
            });
        });

        // Keyboard Navigation for Slides
        document.addEventListener('keydown', (e) => {
            if (intro && e.key === 'Enter') {
                const activeBtn = slides[currentSlide].querySelector('button');
                if (activeBtn) activeBtn.click();
            }
        });
    }

    // Nav Scroll Effect
    const nav = document.querySelector('nav');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    });

    // Parallax Effect
    window.addEventListener('mousemove', (e) => {
        const layers = document.querySelectorAll('.parallax-layer');
        const x = (window.innerWidth - e.pageX * 2) / 100;
        const y = (window.innerHeight - e.pageY * 2) / 100;

        layers.forEach(layer => {
            const speed = layer.getAttribute('data-speed') || 1;
            layer.style.transform = `translateX(${x * speed}px) translateY(${y * speed}px)`;
        });
    });

    // Scroll Reveal with Stagger
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

    // Dynamic FAQ with Loading/Error states
    const faqContainer = document.getElementById('faq-container');
    if (faqContainer) {
        fetch('/static/data/faq.json')
            .then(res => {
                if (!res.ok) throw new Error('Source unavailable');
                return res.json();
            })
            .then(data => {
                if (!data.faq || data.faq.length === 0) {
                    faqContainer.innerHTML = '<div class="text-center p-12 text-gray-400">No questions available currently.</div>';
                    return;
                }
                faqContainer.innerHTML = data.faq.map((item, index) => `
                    <div class="faq-item reveal" style="transition-delay: ${index * 0.1}s">
                        <button class="faq-question w-full text-left" aria-expanded="false">
                            <span>${item.question}</span>
                            <svg class="w-6 h-6 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                        </button>
                        <div class="faq-answer" aria-hidden="true">
                            <p>${item.answer}</p>
                        </div>
                    </div>
                `).join('');

                document.querySelectorAll('.faq-question').forEach(q => {
                    q.addEventListener('click', () => {
                        const item = q.parentElement;
                        const expanded = q.getAttribute('aria-expanded') === 'true';
                        
                        // Accordion behavior
                        document.querySelectorAll('.faq-item').forEach(i => {
                            i.classList.remove('active');
                            i.querySelector('.faq-question').setAttribute('aria-expanded', 'false');
                            i.querySelector('.faq-answer').setAttribute('aria-hidden', 'true');
                        });

                        if (!expanded) {
                            item.classList.add('active');
                            q.setAttribute('aria-expanded', 'true');
                            item.querySelector('.faq-answer').setAttribute('aria-hidden', 'false');
                        }
                    });
                });

                document.querySelectorAll('#faq-container .reveal').forEach(el => revealObserver.observe(el));
            })
            .catch(() => {
                faqContainer.innerHTML = '<div class="text-center p-12 bg-red-50 text-red-600 rounded-3xl font-bold">Infrastructure error: FAQ sync failed.</div>';
            });
    }

    // Smooth Scroll with Header Offset
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            e.preventDefault();
            const target = document.querySelector(targetId);
            if (target) {
                const offset = nav.offsetHeight + 20;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - offset;
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
});
