from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path

from backend.app.core.config import get_settings


def inline_markdown(text: str) -> str:
    escaped = html.escape(text or "")
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\((#[^)]+)\)", r'<a href="\2">\1</a>', escaped)
    return escaped


def render_manual_table(lines: list[str]) -> str:
    rows = []
    for line in lines:
        cells = [inline_markdown(cell.strip()) for cell in line.strip().strip("|").split("|")]
        rows.append(cells)
    if len(rows) >= 2 and all(set(cell.replace(":", "").strip()) <= {"-"} for cell in rows[1]):
        header = rows[0]
        body = rows[2:]
    else:
        header = []
        body = rows
    parts = ['<div class="manual-table-wrap"><table>']
    if header:
        parts.append("<thead><tr>")
        parts.extend(f"<th>{cell}</th>" for cell in header)
        parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in body:
        parts.append("<tr>")
        parts.extend(f"<td>{cell}</td>" for cell in row)
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "\n".join(parts)


def render_manual_markdown(markdown: str) -> str:
    lines = markdown.splitlines()
    parts = []
    i = 0
    in_list = False
    list_tag = "ul"
    in_code = False
    code_lines = []

    def close_list():
        nonlocal in_list, list_tag
        if in_list:
            parts.append(f"</{list_tag}>")
            in_list = False
            list_tag = "ul"

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                parts.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                close_list()
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue
        if not stripped:
            close_list()
            i += 1
            continue
        if stripped.startswith("|") and "|" in stripped[1:]:
            close_list()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            parts.append(render_manual_table(table_lines))
            continue
        image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if image:
            close_list()
            caption = image.group(1).strip()
            source = Path(image.group(2).strip()).name
            safe_caption = html.escape(caption or source)
            parts.append(
                "<figure>"
                f'<img src="/docs/manual-assets/{html.escape(source)}" alt="{safe_caption}" />'
                f"<figcaption>{safe_caption}</figcaption>"
                "</figure>"
            )
            i += 1
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            close_list()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            tag = "h1" if level == 1 else "h2" if level == 2 else "h3"
            heading_id = re.sub(r"[^0-9A-Za-z가-힣]+", "-", text).strip("-")
            parts.append(f'<{tag} id="{html.escape(heading_id)}">{inline_markdown(text)}</{tag}>')
            i += 1
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        number = re.match(r"^\d+\.\s+(.+)$", stripped)
        if bullet or number:
            next_tag = "ol" if number else "ul"
            if in_list and list_tag != next_tag:
                close_list()
            if not in_list:
                list_tag = next_tag
                parts.append(f"<{list_tag}>")
                in_list = True
            parts.append(f"<li>{inline_markdown((bullet or number).group(1))}</li>")
            i += 1
            continue
        close_list()
        parts.append(f"<p>{inline_markdown(stripped)}</p>")
        i += 1
    close_list()
    if in_code:
        parts.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(parts)


def manual_html_page(manual_path: Path | None = None) -> str:
    settings = get_settings()
    manual_path = manual_path or settings.project_root / "docs" / "dobedub-studio-user-manual.md"
    if not manual_path.exists():
        raise FileNotFoundError(manual_path.name)
    markdown = manual_path.read_text(encoding="utf-8")
    modified = datetime.fromtimestamp(manual_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    body = render_manual_markdown(markdown)
    return f"""<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <base href="about:srcdoc" />
    <title>dobedub studio 사용자 매뉴얼</title>
    <style>
      :root {{ color-scheme: light; --blue: #2f80ff; --line: #d6dde8; --muted: #596574; }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; background: #f7f9fc; color: #111827; font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Malgun Gothic", Arial, sans-serif; line-height: 1.62; }}
      main {{ max-width: 980px; margin: 0 auto; padding: 42px 48px 56px; background: #fff; min-height: 100vh; box-shadow: 0 18px 60px rgba(15, 23, 42, 0.12); }}
      h1 {{ margin: 0 0 12px; font-size: 34px; font-weight: 700; letter-spacing: 0; }}
      h2 {{ border-top: 1px solid var(--line); margin: 34px 0 14px; padding-top: 24px; font-size: 25px; letter-spacing: 0; }}
      h3 {{ margin: 24px 0 10px; font-size: 18px; }}
      p {{ margin: 0 0 12px; }}
      ul {{ margin: 0 0 14px 20px; padding: 0; }}
      li {{ margin: 5px 0; }}
      code {{ background: #eef4ff; border: 1px solid #d7e5ff; border-radius: 4px; color: #0f56b3; padding: 1px 5px; }}
      pre {{ background: #111827; border-radius: 8px; color: #f8fafc; overflow: auto; padding: 14px; }}
      figure {{ margin: 18px 0 22px; }}
      figure img {{ border: 1px solid #cbd5e1; border-radius: 8px; display: block; max-width: 100%; width: 100%; }}
      figcaption {{ color: var(--muted); font-size: 13px; margin-top: 8px; text-align: center; }}
      .manual-search {{ align-items: end; background: #fff; border: 1px solid var(--line); border-radius: 10px; display: grid; gap: 10px; grid-template-columns: minmax(180px, 1fr) auto auto; margin: 0 0 22px; padding: 14px; position: sticky; top: 0; z-index: 2; }}
      .manual-search label {{ color: var(--muted); display: grid; font-size: 13px; font-weight: 700; gap: 6px; }}
      .manual-search input {{ border: 1px solid #b9c4d4; border-radius: 6px; font: inherit; min-height: 38px; padding: 8px 10px; }}
      .manual-search button {{ background: var(--blue); border: 0; border-radius: 6px; color: #fff; cursor: pointer; font: inherit; font-weight: 700; min-height: 38px; padding: 8px 14px; }}
      .manual-search button.secondary {{ background: #eef4ff; border: 1px solid #c9dbff; color: #0f56b3; }}
      .manual-search-status {{ color: var(--muted); font-size: 13px; grid-column: 1 / -1; min-height: 18px; }}
      mark.manual-hit {{ background: #fde68a; border-radius: 3px; color: #111827; padding: 0 2px; }}
      mark.manual-hit.is-current {{ background: #fb923c; color: #111827; }}
      .manual-table-wrap {{ overflow-x: auto; margin: 14px 0 20px; }}
      table {{ border-collapse: collapse; min-width: 720px; width: 100%; }}
      th {{ background: #2563eb; color: #fff; font-weight: 700; }}
      th, td {{ border: 1px solid var(--line); padding: 9px 10px; text-align: left; vertical-align: top; }}
      td {{ background: #fbfdff; }}
      @media (max-width: 720px) {{ main {{ padding: 28px 20px 40px; }} h1 {{ font-size: 28px; }} h2 {{ font-size: 22px; }} .manual-search {{ grid-template-columns: 1fr; }} }}
    </style>
  </head>
  <body>
    <main>
      <form class="manual-search" id="manualSearch" role="search">
        <label>매뉴얼 검색
          <input id="manualSearchInput" type="search" placeholder="검색어 입력 후 Enter" autocomplete="off" />
        </label>
        <button type="submit">검색</button>
        <button class="secondary" id="manualSearchNext" type="button">다음</button>
        <div class="manual-search-status" id="manualSearchStatus" aria-live="polite"></div>
      </form>
      <p style="color: var(--muted); margin-bottom: 24px;">Last updated: {html.escape(modified)}</p>
      {body}
    </main>
    <script>
      (() => {{
        const form = document.getElementById("manualSearch");
        const input = document.getElementById("manualSearchInput");
        const nextButton = document.getElementById("manualSearchNext");
        const status = document.getElementById("manualSearchStatus");
        let hits = [];
        let currentIndex = -1;

        // srcDoc documents otherwise resolve fragment links against the host
        // application URL. Keep the table of contents inside this document.
        document.addEventListener("click", (event) => {{
          const target = event.target;
          if (!(target instanceof Element)) {{
            return;
          }}
          const link = target.closest('a[href^="#"]');
          const href = link?.getAttribute("href") || "";
          const anchorId = decodeURIComponent(href.slice(1));
          const section = anchorId ? document.getElementById(anchorId) : null;
          if (!section) {{
            return;
          }}
          event.preventDefault();
          section.scrollIntoView({{ behavior: "smooth", block: "start" }});
        }});

        function clearHighlights() {{
          document.querySelectorAll("mark.manual-hit").forEach((mark) => {{
            const text = document.createTextNode(mark.textContent || "");
            mark.replaceWith(text);
            text.parentNode?.normalize();
          }});
          hits = [];
          currentIndex = -1;
        }}

        function textNodes(root) {{
          const nodes = [];
          const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {{
            acceptNode(node) {{
              if (!node.nodeValue || !node.nodeValue.trim()) {{
                return NodeFilter.FILTER_REJECT;
              }}
              if (node.parentElement?.closest("#manualSearch, script, style, mark")) {{
                return NodeFilter.FILTER_REJECT;
              }}
              return NodeFilter.FILTER_ACCEPT;
            }}
          }});
          while (walker.nextNode()) {{
            nodes.push(walker.currentNode);
          }}
          return nodes;
        }}

        function highlight(term) {{
          clearHighlights();
          const query = term.trim();
          if (!query) {{
            status.textContent = "검색어를 입력하세요.";
            return;
          }}
          const needle = query.toLocaleLowerCase();
          textNodes(document.body).forEach((node) => {{
            const value = node.nodeValue || "";
            const lower = value.toLocaleLowerCase();
            let cursor = 0;
            const fragment = document.createDocumentFragment();
            let found = false;
            while (true) {{
              const index = lower.indexOf(needle, cursor);
              if (index === -1) {{
                break;
              }}
              found = true;
              if (index > cursor) {{
                fragment.appendChild(document.createTextNode(value.slice(cursor, index)));
              }}
              const mark = document.createElement("mark");
              mark.className = "manual-hit";
              mark.textContent = value.slice(index, index + query.length);
              fragment.appendChild(mark);
              cursor = index + query.length;
            }}
            if (!found) {{
              return;
            }}
            if (cursor < value.length) {{
              fragment.appendChild(document.createTextNode(value.slice(cursor)));
            }}
            node.replaceWith(fragment);
          }});
          hits = Array.from(document.querySelectorAll("mark.manual-hit"));
          if (!hits.length) {{
            status.textContent = `"${{query}}" 검색 결과가 없습니다.`;
            return;
          }}
          moveTo(0);
        }}

        function moveTo(index) {{
          if (!hits.length) {{
            status.textContent = "검색 결과가 없습니다.";
            return;
          }}
          hits.forEach((hit) => hit.classList.remove("is-current"));
          currentIndex = (index + hits.length) % hits.length;
          const current = hits[currentIndex];
          current.classList.add("is-current");
          current.scrollIntoView({{ behavior: "smooth", block: "center" }});
          status.textContent = `${{currentIndex + 1}} / ${{hits.length}} 검색 결과`;
        }}

        form?.addEventListener("submit", (event) => {{
          event.preventDefault();
          highlight(input?.value || "");
        }});
        nextButton?.addEventListener("click", () => moveTo(currentIndex + 1));
      }})();
    </script>
  </body>
</html>"""
