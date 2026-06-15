#!/usr/bin/env python3
"""
build_pages.py — Generate 4 static HTML pages from index.html for SEO.
Output: index.html (EN), zh-TW/index.html, zh-CN/index.html, ja/index.html
"""

import re
import os
from html.parser import HTMLParser

# ── Read source ─────────────────────────────────────────────────────────────
with open('/Users/stan/gh/marked2u/index.html', encoding='utf-8') as f:
    src = f.read()

# ── Extract the I18N JS object as raw text ──────────────────────────────────
# We'll parse it manually since it's JS not JSON.
# Strategy: eval each language block by extracting key-value pairs via regex.

# Extract the entire I18N object body
i18n_match = re.search(r'const I18N\s*=\s*\{(.*?)\n\}\s*\n', src, re.DOTALL)
if not i18n_match:
    raise RuntimeError("Could not find I18N object")

i18n_raw = i18n_match.group(0)

# ── Parse each language block ────────────────────────────────────────────────
# Find each top-level lang key: 'zh-TW': { ... }, ...
lang_blocks = {}
lang_pattern = re.compile(r"'(zh-TW|zh-CN|en|ja)'\s*:\s*\{(.*?)\n  \}", re.DOTALL)
for m in lang_pattern.finditer(i18n_raw):
    lang = m.group(1)
    block = m.group(2)
    lang_blocks[lang] = block

if len(lang_blocks) != 4:
    raise RuntimeError(f"Expected 4 lang blocks, found {len(lang_blocks)}: {list(lang_blocks.keys())}")

print(f"Found lang blocks: {list(lang_blocks.keys())}")

def parse_lang_block(block, lang_name):
    """Parse a JS object block into a Python dict."""
    result = {}

    # First extract faq.items array (special handling)
    faq_match = re.search(r"'faq\.items'\s*:\s*\[(.*?)\n    \]", block, re.DOTALL)
    if faq_match:
        faq_raw = faq_match.group(1)
        # Extract each [question, answer] pair
        # Pairs are like: ['Q text', 'A text'],
        items = []
        # Use a state machine approach: find [ ... ] pairs
        # Each item starts with [ and ends with ],
        item_pattern = re.compile(r"\[('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"),\s*('(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\")\]", re.DOTALL)
        for item_m in item_pattern.finditer(faq_raw):
            q_raw = item_m.group(1)
            a_raw = item_m.group(2)
            # Strip surrounding quotes and unescape
            q = q_raw[1:-1].replace("\\'", "'").replace('\\"', '"')
            a = a_raw[1:-1].replace("\\'", "'").replace('\\"', '"')
            items.append((q, a))
        result['faq.items'] = items
        # Remove the faq.items part from block for simpler key parsing
        block = block[:faq_match.start()] + block[faq_match.end():]

    # Parse regular key: 'value' pairs (value may use single or double quotes)
    # Pattern: 'key': 'value' or 'key': "value"
    kv_pattern = re.compile(
        r"'([^']+)'\s*:\s*(?:'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\")",
        re.DOTALL
    )
    for m in kv_pattern.finditer(block):
        key = m.group(1)
        val = m.group(2) if m.group(2) is not None else m.group(3)
        # Unescape JS escape sequences
        val = val.replace("\\'", "'").replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')
        result[key] = val

    return result

# Parse all language data
i18n = {}
for lang, block in lang_blocks.items():
    i18n[lang] = parse_lang_block(block, lang)
    keys = list(i18n[lang].keys())
    faq_count = len(i18n[lang].get('faq.items', []))
    print(f"  {lang}: {len(keys)} keys, {faq_count} FAQ items")

# ── Language config ──────────────────────────────────────────────────────────
LANG_CONFIG = {
    'zh-TW': {
        'html_lang': 'zh-Hant',
        'hreflang': 'zh-Hant',
        'canonical': 'https://md2u.stanwu.org/zh-TW/',
        'output': 'zh-TW/index.html',
        'url_path': '/zh-TW/',
        'subdir': True,
        'ss_dir': '../screenshots',      # zh-TW screenshots
        'link_prefix': '../',
    },
    'zh-CN': {
        'html_lang': 'zh-Hans',
        'hreflang': 'zh-Hans',
        'canonical': 'https://md2u.stanwu.org/zh-CN/',
        'output': 'zh-CN/index.html',
        'url_path': '/zh-CN/',
        'subdir': True,
        'ss_dir': '../screenshots',      # zh-CN screenshots (same as zh-TW)
        'link_prefix': '../',
    },
    'en': {
        'html_lang': 'en',
        'hreflang': 'en',
        'canonical': 'https://md2u.stanwu.org/',
        'output': 'index.html',
        'url_path': '/',
        'subdir': False,
        'ss_dir': 'screenshots/en',
        'link_prefix': '',
    },
    'ja': {
        'html_lang': 'ja',
        'hreflang': 'ja',
        'canonical': 'https://md2u.stanwu.org/ja/',
        'output': 'ja/index.html',
        'url_path': '/ja/',
        'subdir': True,
        'ss_dir': '../screenshots/en',   # ja uses en screenshots
        'link_prefix': '../',
    },
}

HREFLANG_LINKS = """\
  <link rel="alternate" hreflang="en" href="https://md2u.stanwu.org/" />
  <link rel="alternate" hreflang="zh-Hant" href="https://md2u.stanwu.org/zh-TW/" />
  <link rel="alternate" hreflang="zh-Hans" href="https://md2u.stanwu.org/zh-CN/" />
  <link rel="alternate" hreflang="ja" href="https://md2u.stanwu.org/ja/" />
  <link rel="alternate" hreflang="x-default" href="https://md2u.stanwu.org/" />"""

def build_faq_html(items):
    parts = []
    for q, a in items:
        parts.append(
            f'      <div class="faq-item">\n'
            f'        <button class="faq-q">{q}<span class="faq-chevron">▼</span></button>\n'
            f'        <div class="faq-a">{a}</div>\n'
            f'      </div>'
        )
    return '\n'.join(parts)

def build_lang_switcher(active_lang, cfg):
    """Build lang switcher as <a> links."""
    items = [
        ('zh-TW', '繁中', '/zh-TW/'),
        ('zh-CN', '简中', '/zh-CN/'),
        ('en', 'EN', '/'),
        ('ja', '日本語', '/ja/'),
    ]
    parts = []
    for lang_key, label, href in items:
        active = ' active' if lang_key == active_lang else ''
        parts.append(f'      <a class="lang-btn{active}" href="{href}">{label}</a>')
    return '    <div class="lang-switcher">\n' + '\n'.join(parts) + '\n    </div>'

def generate_page(lang, cfg, t):
    html = src

    # 1. Set <html lang="...">
    html = re.sub(r'<html lang="[^"]*">', f'<html lang="{cfg["html_lang"]}">', html)

    # 2. Replace canonical href
    html = html.replace(
        '<link rel="canonical" href="https://md2u.stanwu.org/" />',
        f'<link rel="canonical" href="{cfg["canonical"]}" />\n{HREFLANG_LINKS}'
    )

    # 3. Fill in all data-i18n attributes (non-FAQ)
    def replace_i18n(m):
        tag_open = m.group(1)   # everything up to and including the opening tag
        key_attr = m.group(2)   # the key value
        inner = m.group(3)      # existing inner content (empty)
        tag_close = m.group(4)  # closing tag
        if key_attr == 'faq.label' or key_attr == 'faq.title':
            val = t.get(key_attr, '')
            return f'{tag_open}{val}{tag_close}'
        val = t.get(key_attr, '')
        return f'{tag_open}{val}{tag_close}'

    # Replace elements with data-i18n. Match opening tag ... data-i18n="key" ... > content </tag>
    # We handle void/non-void elements differently via innerHTML approach.
    # Use BeautifulSoup-free approach: regex per element type found in the HTML.

    # For elements that are not self-closing, replace their innerHTML.
    # Pattern: find opening tag with data-i18n, empty content, closing tag.
    # The tags used: a, div, h1, h2, p, span, button
    def fill_i18n(html, t):
        # Match: <TAG ...data-i18n="KEY"...></TAG> with optional whitespace inside
        pattern = re.compile(
            r'(<(?:a|div|h1|h2|h3|p|span|button)[^>]*\bdata-i18n="([^"]+)"[^>]*>)'
            r'([^<]*)'
            r'(</(?:a|div|h1|h2|h3|p|span|button)>)',
            re.DOTALL
        )
        def replacer(m):
            key = m.group(2)
            if key in t and not isinstance(t[key], list):
                return m.group(1) + t[key] + m.group(4)
            return m.group(0)
        return pattern.sub(replacer, html)

    html = fill_i18n(html, t)

    # 4. Replace lang switcher
    old_switcher_pattern = re.compile(
        r'<div class="lang-switcher">.*?</div>',
        re.DOTALL
    )
    new_switcher = build_lang_switcher(lang, cfg)
    html = old_switcher_pattern.sub(new_switcher, html, count=1)

    # 5. Replace screenshot src paths
    ss_dir = cfg['ss_dir']
    # Replace all src="screenshots/..." in one pass to avoid double-substitution.
    # The original HTML has: screenshots/preview.png and screenshots/find.png etc.
    # (All without subdirectory prefix — the original has no /en/ subfolder in gallery imgs.)
    def replace_all_ss(m):
        filename = m.group(1)  # e.g. "preview.png", "find.png"
        return f'src="{ss_dir}/{filename}"'
    html = re.sub(r'src="screenshots/([^"/]+\.png)"', replace_all_ss, html)

    # 6. Fix relative links for subdirs (code-signing-policy.html, privacy-policy.html)
    if cfg['subdir']:
        prefix = cfg['link_prefix']
        html = html.replace('href="code-signing-policy.html"', f'href="{prefix}code-signing-policy.html"')
        html = html.replace('href="privacy-policy.html"', f'href="{prefix}privacy-policy.html"')
        # Also fix privacy-policy.html links in FAQ answers (already inlined above)
        # These will be in the rendered FAQ HTML — handle after FAQ render

    # 7. Render FAQ
    faq_items = t.get('faq.items', [])
    faq_html = build_faq_html(faq_items)
    if cfg['subdir']:
        # Fix privacy-policy.html links in FAQ
        faq_html = faq_html.replace('href="privacy-policy.html"', f'href="{cfg["link_prefix"]}privacy-policy.html"')
    html = html.replace(
        '<div id="faq-list" style="margin-top:40px;display:flex;flex-direction:column;gap:0"></div>',
        f'<div id="faq-list" style="margin-top:40px;display:flex;flex-direction:column;gap:0">\n{faq_html}\n    </div>'
    )

    # 8. Remove the entire <script> block (I18N object, detectLang, applyLang, etc.)
    # Keep only the FAQ accordion click handler
    faq_js = """\
<script>
document.querySelectorAll('.faq-q').forEach(btn => {
  btn.addEventListener('click', () => btn.parentElement.classList.toggle('open'))
})
</script>"""

    # Remove the big script block
    html = re.sub(r'<script>\s*const I18N.*?</script>', faq_js, html, flags=re.DOTALL)

    return html

# ── Generate each page ───────────────────────────────────────────────────────
base = '/Users/stan/gh/marked2u'

for lang, cfg in LANG_CONFIG.items():
    t = i18n[lang]
    page_html = generate_page(lang, cfg, t)

    out_path = os.path.join(base, cfg['output'])
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(page_html)

    print(f"Written: {cfg['output']} ({len(page_html)} bytes)")

# ── Generate sitemap.xml ─────────────────────────────────────────────────────
sitemap = """\
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://md2u.stanwu.org/</loc>
    <xhtml:link rel="alternate" hreflang="en" href="https://md2u.stanwu.org/"/>
    <xhtml:link rel="alternate" hreflang="zh-Hant" href="https://md2u.stanwu.org/zh-TW/"/>
    <xhtml:link rel="alternate" hreflang="zh-Hans" href="https://md2u.stanwu.org/zh-CN/"/>
    <xhtml:link rel="alternate" hreflang="ja" href="https://md2u.stanwu.org/ja/"/>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url><loc>https://md2u.stanwu.org/zh-TW/</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>
  <url><loc>https://md2u.stanwu.org/zh-CN/</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>
  <url><loc>https://md2u.stanwu.org/ja/</loc><changefreq>weekly</changefreq><priority>0.9</priority></url>
</urlset>
"""

with open(os.path.join(base, 'sitemap.xml'), 'w', encoding='utf-8') as f:
    f.write(sitemap)
print("Written: sitemap.xml")

print("\nDone.")
