// MathJax configuration for TINAA documentation
// Supports mathematical notation for performance metrics and algorithms

window.MathJaxConfig = function () {
  MathJax.Hub.Config({
    tex2jax: {
      inlineMath: [['$', '$'], ['\\(', '\\)']],
      displayMath: [['$$', '$$'], ['\\[', '\\]']],
      processEscapes: true,
      processEnvironments: true,
      skipTags: ['script', 'noscript', 'style', 'textarea', 'pre'],
      TeX: {
        equationNumbers: { autoNumber: "AMS" },
        extensions: ["AMSmath.js", "AMSsymbols.js", "noErrors.js", "noUndefined.js"]
      }
    },
    "HTML-CSS": {
      fonts: ["TeX"],
      linebreaks: { automatic: true },
      scale: 90
    },
    SVG: {
      linebreaks: { automatic: true }
    }
  });
  
  MathJax.Hub.Register.MessageHook("Math Processing Error", function (message) {
    console.error("MathJax Error:", message[2].message);
  });
};

// Initialize MathJax when ready
document.addEventListener('DOMContentLoaded', function() {
  if (typeof MathJax !== 'undefined') {
    MathJaxConfig();
  }
});