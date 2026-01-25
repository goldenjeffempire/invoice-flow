document.addEventListener('DOMContentLoaded', () => {
    // Intro Slides Logic
    const intro = document.getElementById('intro-slides');
    const slides = document.querySelectorAll('.slide');
    const nextButtons = document.querySelectorAll('.next-slide');
    let currentSlide = 0;

    // Check if seen intro
    if (localStorage.getItem('introSeen')) {
        if (intro) intro.style.display = 'none';
    } else {
        nextButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                slides[currentSlide].classList.remove('active');
                currentSlide++;
                if (currentSlide < slides.length) {
                    slides[currentSlide].classList.add('active');
                } else {
                    intro.style.opacity = '0';
                    setTimeout(() => {
                        intro.style.display = 'none';
                        localStorage.setItem('introSeen', 'true');
                    }, 500);
                }
            });
        });
    }

    // Dynamic FAQ
    const faqContainer = document.getElementById('faq-container');
    if (faqContainer) {
        fetch('/static/data/faq.json')
            .then(res => {
                if (!res.ok) throw new Error('Network error');
                return res.json();
            })
            .then(data => {
                faqContainer.innerHTML = data.faq.map(item => `
                    <div class="faq-item animate-reveal">
                        <h4>${item.question}</h4>
                        <p class="text-muted">${item.answer}</p>
                    </div>
                `).join('');
                // Observe new elements
                document.querySelectorAll('.faq-item').forEach(el => observer.observe(el));
            })
            .catch(err => {
                console.error(err);
                faqContainer.innerHTML = '<div class="error p-4 text-red-500">Failed to load FAQs. Please refresh the page.</div>';
            });
    }

    // Intersection Observer for animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                observer.unobserve(entry.target);
            }
        });
    }, { 
        threshold: 0.15,
        rootMargin: '0px 0px -50px 0px'
    });

    document.querySelectorAll('.animate-reveal').forEach(el => observer.observe(el));

    // Smooth Scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});
