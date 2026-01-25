(function() {
  'use strict';

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  const state = {
    introComplete: false,
    currentSlide: 0,
    totalSlides: 3,
    faqLoaded: false,
    mobileMenuOpen: false
  };

  function initIntroSlides() {
    const overlay = document.querySelector('.intro-overlay');
    if (!overlay) return;

    const slides = overlay.querySelectorAll('.slide-content');
    const dots = overlay.querySelectorAll('.intro-dot');
    const skipBtn = overlay.querySelector('.intro-skip');
    
    if (slides.length === 0) {
      completeIntro();
      return;
    }

    if (prefersReducedMotion) {
      completeIntro();
      return;
    }

    const hasSeenIntro = sessionStorage.getItem('introSeen');
    if (hasSeenIntro) {
      completeIntro();
      return;
    }

    slides[0].classList.add('active');
    if (dots[0]) dots[0].classList.add('active');

    function showSlide(index) {
      slides.forEach((slide, i) => {
        slide.classList.remove('active', 'exit');
        if (i < index) slide.classList.add('exit');
      });
      
      slides[index].classList.add('active');
      
      dots.forEach((dot, i) => {
        dot.classList.toggle('active', i === index);
      });
      
      state.currentSlide = index;
    }

    function nextSlide() {
      if (state.currentSlide < state.totalSlides - 1) {
        showSlide(state.currentSlide + 1);
      } else {
        completeIntro();
      }
    }

    dots.forEach((dot, index) => {
      dot.addEventListener('click', () => showSlide(index));
      dot.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          showSlide(index);
        }
      });
    });

    if (skipBtn) {
      skipBtn.addEventListener('click', completeIntro);
      skipBtn.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          completeIntro();
        }
      });
    }

    document.addEventListener('keydown', (e) => {
      if (state.introComplete) return;
      
      if (e.key === 'Escape') {
        completeIntro();
      } else if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault();
        nextSlide();
      } else if (e.key === 'ArrowLeft' && state.currentSlide > 0) {
        e.preventDefault();
        showSlide(state.currentSlide - 1);
      }
    });

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay || e.target.classList.contains('parallax-bg')) {
        nextSlide();
      }
    });

    const slideInterval = setInterval(() => {
      if (state.introComplete) {
        clearInterval(slideInterval);
        return;
      }
      nextSlide();
    }, 3500);

    overlay.dataset.interval = slideInterval;
  }

  function completeIntro() {
    if (state.introComplete) return;
    state.introComplete = true;
    
    const overlay = document.querySelector('.intro-overlay');
    if (overlay) {
      const interval = overlay.dataset.interval;
      if (interval) clearInterval(Number(interval));
      
      overlay.classList.add('hidden');
      
      setTimeout(() => {
        overlay.remove();
      }, 800);
    }
    
    sessionStorage.setItem('introSeen', 'true');
    
    initScrollReveal();
    initScrollProgress();
  }

  function initScrollReveal() {
    const reveals = document.querySelectorAll('.reveal');
    
    if (prefersReducedMotion) {
      reveals.forEach(el => el.classList.add('visible'));
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          // Add staggered delay to children if needed
          if (entry.target.classList.contains('stagger-children')) {
            entry.target.classList.add('visible');
          }
        }
      });
    }, {
      threshold: 0.15,
      rootMargin: '0px 0px -10% 0px'
    });

    reveals.forEach(el => observer.observe(el));
  }

  function initScrollProgress() {
    const indicator = document.querySelector('.scroll-indicator');
    if (!indicator) return;

    function updateProgress() {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      const progress = Math.min(scrollTop / docHeight, 1);
      indicator.style.transform = `scaleX(${progress})`;
    }

    window.addEventListener('scroll', updateProgress, { passive: true });
    updateProgress();
  }

  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;
        
        const target = document.querySelector(targetId);
        if (target) {
          e.preventDefault();
          
          const navHeight = document.querySelector('nav')?.offsetHeight || 80;
          const targetPosition = target.getBoundingClientRect().top + window.scrollY - navHeight;
          
          if (prefersReducedMotion) {
            window.scrollTo(0, targetPosition);
          } else {
            window.scrollTo({
              top: targetPosition,
              behavior: 'smooth'
            });
          }

          closeMobileMenu();
          
          target.setAttribute('tabindex', '-1');
          target.focus();
        }
      });
    });
  }

  async function initFAQ() {
    const container = document.getElementById('dynamic-faq');
    if (!container) return;

    container.innerHTML = `
      <div class="space-y-4">
        ${Array(4).fill().map(() => `
          <div class="faq-skeleton bg-slate-100 rounded-3xl h-20"></div>
        `).join('')}
      </div>
    `;

    try {
      const response = await fetch('/api/faq/');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.faqs || data.faqs.length === 0) {
        container.innerHTML = `
          <div class="faq-empty">
            <svg class="mx-auto h-12 w-12 text-slate-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="font-semibold">No FAQs available at the moment</p>
          </div>
        `;
        return;
      }
      
      renderFAQ(container, data.faqs);
      state.faqLoaded = true;
      
    } catch (error) {
      console.error('FAQ loading error:', error);
      container.innerHTML = `
        <div class="faq-error">
          <svg class="mx-auto h-12 w-12 text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p class="font-semibold mb-2">Unable to load FAQs</p>
          <button onclick="location.reload()" class="text-sm text-red-600 hover:text-red-700 underline">Try again</button>
        </div>
      `;
    }
  }

  function renderFAQ(container, faqs) {
    container.innerHTML = `
      <div class="space-y-4" role="list">
        ${faqs.map((faq, index) => `
          <div class="faq-item" role="listitem">
            <button 
              class="faq-trigger" 
              aria-expanded="false" 
              aria-controls="faq-content-${faq.id}"
              id="faq-trigger-${faq.id}"
            >
              <span>${faq.question}</span>
              <span class="faq-icon" aria-hidden="true">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </span>
            </button>
            <div 
              class="faq-content" 
              id="faq-content-${faq.id}"
              role="region"
              aria-labelledby="faq-trigger-${faq.id}"
            >
              <div class="faq-answer">${faq.answer}</div>
            </div>
          </div>
        `).join('')}
      </div>
    `;

    container.querySelectorAll('.faq-trigger').forEach(trigger => {
      trigger.addEventListener('click', function() {
        const item = this.closest('.faq-item');
        const isOpen = item.classList.contains('open');
        const content = item.querySelector('.faq-content');
        
        container.querySelectorAll('.faq-item').forEach(otherItem => {
          if (otherItem !== item) {
            otherItem.classList.remove('open');
            otherItem.querySelector('.faq-trigger').setAttribute('aria-expanded', 'false');
          }
        });
        
        item.classList.toggle('open', !isOpen);
        this.setAttribute('aria-expanded', !isOpen);
      });

      trigger.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.click();
        }
      });
    });
  }

  function initMobileMenu() {
    const menuBtn = document.getElementById('mobile-menu-btn');
    const closeBtn = document.getElementById('mobile-menu-close');
    const menu = document.getElementById('mobile-menu');
    const backdrop = document.getElementById('mobile-menu-backdrop');
    
    if (!menuBtn || !menu) return;

    function openMobileMenu() {
      state.mobileMenuOpen = true;
      menu.classList.add('open');
      if (backdrop) backdrop.classList.add('open');
      document.body.style.overflow = 'hidden';
      menuBtn.setAttribute('aria-expanded', 'true');
    }

    function closeMobileMenuHandler() {
      closeMobileMenu();
    }

    menuBtn.addEventListener('click', openMobileMenu);
    if (closeBtn) closeBtn.addEventListener('click', closeMobileMenuHandler);
    if (backdrop) backdrop.addEventListener('click', closeMobileMenuHandler);

    menu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', closeMobileMenuHandler);
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && state.mobileMenuOpen) {
        closeMobileMenuHandler();
      }
    });
  }

  function closeMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    const backdrop = document.getElementById('mobile-menu-backdrop');
    const menuBtn = document.getElementById('mobile-menu-btn');
    
    state.mobileMenuOpen = false;
    if (menu) menu.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
    document.body.style.overflow = '';
    if (menuBtn) menuBtn.setAttribute('aria-expanded', 'false');
  }

  function initNavScroll() {
    const nav = document.querySelector('nav');
    if (!nav) return;

    let lastScroll = 0;
    const threshold = 100;

    window.addEventListener('scroll', () => {
      const currentScroll = window.scrollY;
      
      if (currentScroll > threshold) {
        nav.classList.add('nav-scrolled');
      } else {
        nav.classList.remove('nav-scrolled');
      }
      
      lastScroll = currentScroll;
    }, { passive: true });
  }

  function initParallax() {
    if (prefersReducedMotion) return;

    const parallaxElements = document.querySelectorAll('.parallax-bg');
    
    window.addEventListener('scroll', () => {
      const scrollY = window.scrollY;
      
      parallaxElements.forEach(el => {
        const speed = 0.3;
        el.style.transform = `translateY(${scrollY * speed}px)`;
      });
    }, { passive: true });
  }

  function initContactForm() {
    const form = document.getElementById('contact-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const submitBtn = form.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;
      submitBtn.textContent = 'Sending...';
      submitBtn.disabled = true;

      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const successMsg = document.createElement('div');
      successMsg.className = 'mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700 font-medium';
      successMsg.textContent = 'Thank you for your message! We\'ll get back to you soon.';
      form.appendChild(successMsg);
      
      form.reset();
      submitBtn.textContent = originalText;
      submitBtn.disabled = false;

      setTimeout(() => successMsg.remove(), 5000);
    });
  }

  function checkScrollToSection() {
    const urlParams = new URLSearchParams(window.location.search);
    const scrollTo = document.body.dataset.scrollTo || urlParams.get('section');
    
    if (scrollTo) {
      const target = document.getElementById(scrollTo);
      if (target) {
        setTimeout(() => {
          const navHeight = document.querySelector('nav')?.offsetHeight || 80;
          window.scrollTo({
            top: target.offsetTop - navHeight,
            behavior: prefersReducedMotion ? 'auto' : 'smooth'
          });
        }, 100);
      }
    }
  }

  function init() {
    initIntroSlides();
    initSmoothScroll();
    initFAQ();
    initMobileMenu();
    initNavScroll();
    initParallax();
    initContactForm();
    
    setTimeout(() => {
      if (!state.introComplete) {
        initScrollReveal();
        initScrollProgress();
      }
      checkScrollToSection();
    }, 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
