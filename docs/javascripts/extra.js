// TINAA Custom JavaScript

// Initialize Material theme components
document.addEventListener('DOMContentLoaded', function() {
  // Copy code button enhancement
  const codeBlocks = document.querySelectorAll('pre > code');
  codeBlocks.forEach((codeBlock) => {
    const button = codeBlock.parentElement.querySelector('.md-clipboard');
    if (button) {
      button.addEventListener('click', function() {
        // Show copied feedback
        const originalTitle = button.getAttribute('title');
        button.setAttribute('title', 'Copied!');
        setTimeout(() => {
          button.setAttribute('title', originalTitle);
        }, 2000);
      });
    }
  });

  // Terminal animation for demo sections
  const terminals = document.querySelectorAll('.terminal-cursor');
  terminals.forEach((terminal) => {
    let text = terminal.textContent;
    terminal.textContent = '';
    let i = 0;
    
    function typeWriter() {
      if (i < text.length) {
        terminal.textContent += text.charAt(i);
        i++;
        setTimeout(typeWriter, 50);
      }
    }
    
    // Start animation when element is in viewport
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          typeWriter();
          observer.unobserve(entry.target);
        }
      });
    });
    
    observer.observe(terminal);
  });

  // Smooth scrolling for anchor links
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

  // Add loading animation to API examples
  const apiExamples = document.querySelectorAll('.api-example');
  apiExamples.forEach((example) => {
    const runButton = document.createElement('button');
    runButton.className = 'md-button md-button--primary api-run-button';
    runButton.textContent = 'Run Example';
    runButton.onclick = function() {
      runButton.disabled = true;
      runButton.textContent = 'Running...';
      
      // Simulate API call
      setTimeout(() => {
        runButton.textContent = 'Success!';
        runButton.classList.add('success');
        setTimeout(() => {
          runButton.disabled = false;
          runButton.textContent = 'Run Example';
          runButton.classList.remove('success');
        }, 2000);
      }, 1500);
    };
    
    example.appendChild(runButton);
  });

  // Feature card hover effects
  const featureCards = document.querySelectorAll('.feature-box, .grid > .card');
  featureCards.forEach((card) => {
    card.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-4px)';
    });
    
    card.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0)';
    });
  });

  // Search enhancement
  const searchInput = document.querySelector('.md-search__input');
  if (searchInput) {
    searchInput.addEventListener('focus', function() {
      document.body.classList.add('search-focused');
    });
    
    searchInput.addEventListener('blur', function() {
      document.body.classList.remove('search-focused');
    });
  }

  // Version selector enhancement
  const versionSelector = document.querySelector('.md-version__current');
  if (versionSelector) {
    versionSelector.addEventListener('click', function() {
      this.classList.toggle('md-version__current--active');
    });
  }

  // Progress indicator for long pages
  const progressBar = document.createElement('div');
  progressBar.className = 'reading-progress';
  document.body.appendChild(progressBar);
  
  window.addEventListener('scroll', function() {
    const windowHeight = window.innerHeight;
    const documentHeight = document.documentElement.scrollHeight - windowHeight;
    const scrolled = window.scrollY;
    const progress = (scrolled / documentHeight) * 100;
    
    progressBar.style.width = progress + '%';
    
    if (progress > 0) {
      progressBar.style.opacity = '1';
    } else {
      progressBar.style.opacity = '0';
    }
  });

  // Interactive metric counters
  const metrics = document.querySelectorAll('.success-metrics .metric .value');
  metrics.forEach((metric) => {
    const finalValue = parseInt(metric.textContent);
    let currentValue = 0;
    const increment = finalValue / 50;
    
    const counter = setInterval(() => {
      currentValue += increment;
      if (currentValue >= finalValue) {
        currentValue = finalValue;
        clearInterval(counter);
      }
      metric.textContent = Math.floor(currentValue) + (metric.textContent.includes('%') ? '%' : '');
    }, 30);
  });
});

// Add keyboard shortcuts
document.addEventListener('keydown', function(e) {
  // Ctrl/Cmd + K for search
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const searchInput = document.querySelector('.md-search__input');
    if (searchInput) {
      searchInput.focus();
    }
  }
  
  // Escape to close search
  if (e.key === 'Escape') {
    const searchInput = document.querySelector('.md-search__input');
    if (searchInput && document.activeElement === searchInput) {
      searchInput.blur();
    }
  }
});

// Add custom styles for progress bar
const style = document.createElement('style');
style.textContent = `
  .reading-progress {
    position: fixed;
    top: 0;
    left: 0;
    height: 3px;
    background: var(--md-primary-fg-color);
    z-index: 1000;
    transition: width 0.2s, opacity 0.2s;
    opacity: 0;
  }
  
  .api-run-button {
    margin-top: 1rem;
    transition: all 0.3s;
  }
  
  .api-run-button.success {
    background-color: #4caf50;
    border-color: #4caf50;
  }
  
  .search-focused .md-search__form {
    box-shadow: 0 0 0 3px var(--md-accent-fg-color--transparent);
  }
`;
document.head.appendChild(style);

// MathJax configuration for technical documentation
window.MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\(', '\\)']],
    displayMath: [['$$', '$$'], ['\\[', '\\]']],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: '.*|',
    processHtmlClass: 'arithmatex'
  }
};