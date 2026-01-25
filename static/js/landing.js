document.addEventListener('DOMContentLoaded', () => {
    // Scroll reveals
    const observerOptions = {
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('reveal-visible');
            }
        });
    }, observerOptions);

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

    // Intro Slides
    const introSlides = document.querySelector('.intro-slides');
    if (introSlides) {
        let currentSlide = 0;
        const slides = document.querySelectorAll('.intro-slide');
        
        const nextSlide = () => {
            slides[currentSlide].classList.remove('active');
            slides[currentSlide].classList.add('prev');
            currentSlide++;
            
            if (currentSlide < slides.length) {
                slides[currentSlide].classList.add('active');
                setTimeout(nextSlide, 3000);
            } else {
                introSlides.classList.add('hidden');
                document.body.classList.remove('overflow-hidden');
            }
        };

        setTimeout(nextSlide, 3000);
    }
});