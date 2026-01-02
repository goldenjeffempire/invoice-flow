/**
 * InvoiceFlow Performance Utilities
 * Progressive enhancement and performance monitoring
 */

(function() {
  'use strict';

  var PerformanceUtils = {
    prefersReducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    
    connectionType: (navigator.connection || navigator.mozConnection || navigator.webkitConnection || {}).effectiveType || '4g',
    
    saveData: (navigator.connection || {}).saveData === true,

    init: function() {
      this.setupConnectionMonitoring();
      this.applyPerformanceOptimizations();
      this.setupResourceHints();
      this.trackCoreWebVitals();
    },

    setupConnectionMonitoring: function() {
      var self = this;
      var connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      
      if (connection) {
        connection.addEventListener('change', function() {
          self.connectionType = connection.effectiveType || '4g';
          self.saveData = connection.saveData === true;
          self.applyPerformanceOptimizations();
        });
      }
    },

    applyPerformanceOptimizations: function() {
      var body = document.body;
      
      body.classList.remove('connection-slow', 'connection-fast', 'save-data');
      
      if (this.saveData) {
        body.classList.add('save-data');
        this.disableAutoplay();
        this.reduceImageQuality();
      }
      
      if (this.connectionType === 'slow-2g' || this.connectionType === '2g') {
        body.classList.add('connection-slow');
        this.loadLowResImages();
      } else if (this.connectionType === '4g') {
        body.classList.add('connection-fast');
      }
      
      if (this.prefersReducedMotion) {
        body.classList.add('reduced-motion');
        this.disableAnimations();
      }
    },

    disableAutoplay: function() {
      var videos = document.querySelectorAll('video[autoplay]');
      videos.forEach(function(video) {
        video.removeAttribute('autoplay');
        video.pause();
      });
    },

    reduceImageQuality: function() {
      var images = document.querySelectorAll('img[data-src-low]');
      images.forEach(function(img) {
        img.dataset.src = img.dataset.srcLow;
      });
    },

    loadLowResImages: function() {
      var images = document.querySelectorAll('img[data-src-low]');
      images.forEach(function(img) {
        if (img.dataset.srcLow) {
          img.src = img.dataset.srcLow;
        }
      });
    },

    disableAnimations: function() {
      var style = document.createElement('style');
      style.textContent = '*, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; }';
      document.head.appendChild(style);
    },

    setupResourceHints: function() {
      var self = this;
      
      var links = document.querySelectorAll('a[href^="/"], a[href^="' + window.location.origin + '"]');
      
      if ('IntersectionObserver' in window && this.connectionType === '4g' && !this.saveData) {
        var observer = new IntersectionObserver(function(entries) {
          entries.forEach(function(entry) {
            if (entry.isIntersecting) {
              self.prefetchLink(entry.target.href);
              observer.unobserve(entry.target);
            }
          });
        }, { rootMargin: '0px 0px 50px 0px' });
        
        links.forEach(function(link) {
          observer.observe(link);
        });
      }
    },

    prefetchLink: function(href) {
      if (document.querySelector('link[rel="prefetch"][href="' + href + '"]')) {
        return;
      }
      
      var link = document.createElement('link');
      link.rel = 'prefetch';
      link.href = href;
      link.as = 'document';
      document.head.appendChild(link);
    },

    trackCoreWebVitals: function() {
      if (!('PerformanceObserver' in window)) return;

      try {
        new PerformanceObserver(function(entryList) {
          var entries = entryList.getEntries();
          entries.forEach(function(entry) {
            if (entry.name === 'first-contentful-paint') {
              // FCP tracked
            }
          });
        }).observe({ entryTypes: ['paint'] });
      } catch (e) {}

      try {
        new PerformanceObserver(function(entryList) {
          var entries = entryList.getEntries();
          entries.forEach(function(entry) {
            // LCP tracked
          });
        }).observe({ entryTypes: ['largest-contentful-paint'] });
      } catch (e) {}

      try {
        new PerformanceObserver(function(entryList) {
          var entries = entryList.getEntries();
          entries.forEach(function(entry) {
            if (!entry.hadRecentInput) {
              // CLS tracked
            }
          });
        }).observe({ entryTypes: ['layout-shift'] });
      } catch (e) {}

      try {
        new PerformanceObserver(function(entryList) {
          var entries = entryList.getEntries();
          entries.forEach(function(entry) {
            // FID tracked
          });
        }).observe({ entryTypes: ['first-input'] });
      } catch (e) {}
    },

    measureNavigation: function() {
      if (!window.performance || !window.performance.timing) return null;

      var timing = window.performance.timing;
      return {
        dns: timing.domainLookupEnd - timing.domainLookupStart,
        tcp: timing.connectEnd - timing.connectStart,
        ttfb: timing.responseStart - timing.navigationStart,
        domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
        load: timing.loadEventEnd - timing.navigationStart
      };
    }
  };

  window.PerformanceUtils = PerformanceUtils;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      PerformanceUtils.init();
    });
  } else {
    PerformanceUtils.init();
  }

})();
