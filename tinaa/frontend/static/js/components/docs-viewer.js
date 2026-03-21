/**
 * docs-viewer.js — Documentation Viewer Web Component.
 *
 * Renders Markdown-like content as accessible HTML with:
 * - Basic Markdown parsing (headings, code blocks, bold, italic, lists, links)
 * - Table of contents auto-generated from headings
 * - Proper heading hierarchy
 * - Code block syntax highlighting via CSS only
 *
 * Usage:
 *   <tinaa-docs-viewer></tinaa-docs-viewer>
 *   el.setContent("# Title\n\nMarkdown content…")
 */

/**
 * Minimal Markdown-to-HTML converter.
 * Handles: headings, code blocks, inline code, bold, italic,
 * unordered/ordered lists, links, blockquotes, horizontal rules, paragraphs.
 *
 * @param {string} md - Raw markdown string
 * @returns {string} HTML string
 */
function markdownToHtml(md) {
  if (!md) return "";

  // Protect code blocks first (to avoid inner parsing)
  const codeBlocks = [];
  let html = md.replace(/```([\w]*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(
      `<pre><code class="language-${lang || "text"}">${escapeHtml(code.trim())}</code></pre>`
    );
    return `%%CODEBLOCK_${idx}%%`;
  });

  // Process line by line
  const lines = html.split("\n");
  const output = [];
  let inList = null;   // "ul" | "ol" | null
  let inOrderedList = false;

  const closeList = () => {
    if (inList) { output.push(`</${inList}>`); inList = null; }
  };

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Headings
    const hMatch = line.match(/^(#{1,6})\s+(.*)/);
    if (hMatch) {
      closeList();
      const level = hMatch[1].length;
      const text  = inlineMarkdown(hMatch[2]);
      const id    = hMatch[2].toLowerCase().replace(/[^a-z0-9]+/g, "-");
      output.push(`<h${level} id="${id}">${text}</h${level}>`);
      continue;
    }

    // Horizontal rule
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(line.trim())) {
      closeList();
      output.push("<hr />");
      continue;
    }

    // Blockquote
    if (line.startsWith("> ")) {
      closeList();
      output.push(`<blockquote>${inlineMarkdown(line.slice(2))}</blockquote>`);
      continue;
    }

    // Unordered list
    if (/^[-*+]\s+/.test(line)) {
      if (inList !== "ul") { closeList(); output.push("<ul>"); inList = "ul"; }
      output.push(`<li>${inlineMarkdown(line.replace(/^[-*+]\s+/, ""))}</li>`);
      continue;
    }

    // Ordered list
    if (/^\d+\.\s+/.test(line)) {
      if (inList !== "ol") { closeList(); output.push("<ol>"); inList = "ol"; }
      output.push(`<li>${inlineMarkdown(line.replace(/^\d+\.\s+/, ""))}</li>`);
      continue;
    }

    closeList();

    // Empty line
    if (line.trim() === "") {
      output.push("");
      continue;
    }

    // Code block placeholder
    if (line.startsWith("%%CODEBLOCK_")) {
      const idx = parseInt(line.replace(/%%CODEBLOCK_(\d+)%%/, "$1"), 10);
      output.push(codeBlocks[idx] || "");
      continue;
    }

    // Paragraph
    output.push(`<p>${inlineMarkdown(line)}</p>`);
  }

  closeList();
  return output.join("\n");
}

/** Process inline Markdown: bold, italic, inline code, links. */
function inlineMarkdown(text) {
  return text
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/_([^_]+)_/g, "<em>$1</em>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
}

/** Escape HTML special characters. */
function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/** Extract headings from HTML for TOC generation. */
function extractHeadings(html) {
  const matches = [];
  const re = /<h([1-6])\s+id="([^"]+)">([^<]*)/g;
  let m;
  while ((m = re.exec(html)) !== null) {
    matches.push({ level: parseInt(m[1]), id: m[2], text: m[3] });
  }
  return matches;
}

class TINAADocsViewer extends HTMLElement {
  constructor() {
    super();
    this._content = "";
    this._loading = false;
  }

  connectedCallback() {
    this.render();
  }

  /**
   * @param {string} markdown - Raw markdown content to render
   */
  setContent(markdown) {
    this._content = markdown || "";
    this._loading = false;
    this.render();
  }

  setLoading() {
    this._loading = true;
    this.render();
  }

  render() {
    if (this._loading) {
      this.innerHTML = `
        <div class="animate-pulse space-y-3 py-4" aria-busy="true" aria-label="Loading documentation">
          <div class="h-6 bg-slate-700 rounded w-1/3"></div>
          <div class="h-4 bg-slate-700 rounded w-full"></div>
          <div class="h-4 bg-slate-700 rounded w-5/6"></div>
          <div class="h-4 bg-slate-700 rounded w-4/6"></div>
        </div>
      `;
      return;
    }

    const htmlContent = markdownToHtml(this._content);
    const headings    = extractHeadings(htmlContent);

    const tocHtml = headings.length > 0
      ? `<nav aria-label="Table of contents" class="mb-6 p-3 bg-slate-800 rounded-lg border
                 border-slate-700 text-sm">
           <p class="font-semibold text-slate-300 mb-2">Contents</p>
           <ol class="space-y-1" role="list">
             ${headings.map((h) => `
               <li style="padding-left:${(h.level - 1) * 12}px" role="listitem">
                 <a href="#${h.id}"
                    class="text-blue-400 hover:text-blue-300 transition-colors
                           focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
                           rounded">
                   ${h.text}
                 </a>
               </li>
             `).join("")}
           </ol>
         </nav>`
      : "";

    this.innerHTML = `
      <div class="docs-viewer-wrapper">
        ${tocHtml}
        <div class="docs-content prose-slate">
          ${htmlContent || '<p class="text-slate-400">No content available.</p>'}
        </div>
      </div>
    `;
  }
}

customElements.define("tinaa-docs-viewer", TINAADocsViewer);
