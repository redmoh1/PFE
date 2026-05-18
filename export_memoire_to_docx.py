from __future__ import annotations

import argparse
import html
import subprocess
import tempfile
from pathlib import Path

import markdown


HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{
      font-family: Calibri, Arial, sans-serif;
      font-size: 12pt;
      line-height: 1.45;
      margin: 2.2cm;
      color: #111;
    }}
    h1, h2, h3, h4 {{
      color: #111;
      margin-top: 18pt;
      margin-bottom: 8pt;
    }}
    h1 {{ font-size: 18pt; text-align: center; }}
    h2 {{ font-size: 15pt; }}
    h3 {{ font-size: 13pt; }}
    p {{ margin: 0 0 8pt 0; }}
    ul, ol {{ margin: 0 0 8pt 20pt; }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 10pt 0;
      font-size: 11pt;
    }}
    th, td {{
      border: 1px solid #444;
      padding: 6pt;
      vertical-align: top;
    }}
    th {{ background: #efefef; }}
    hr {{ border: 0; border-top: 1px solid #999; margin: 14pt 0; }}
    code {{ font-family: Consolas, monospace; }}
    .page-break {{ page-break-after: always; }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def build_html(markdown_text: str, title: str) -> str:
    normalized = markdown_text.replace("\\newpage", '<div class="page-break"></div>')
    body = markdown.markdown(
        normalized,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
        output_format="html5",
    )
    return HTML_TEMPLATE.format(title=html.escape(title), body=body)


def powershell_escape(value: str) -> str:
    return value.replace("'", "''")


def convert_html_to_docx(html_path: Path, docx_path: Path) -> None:
    html_arg = powershell_escape(str(html_path))
    docx_arg = powershell_escape(str(docx_path))
    script = f"""
$ErrorActionPreference = 'Stop'
$word = $null
$document = $null
try {{
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open('{html_arg}')
    $document.SaveAs2('{docx_arg}', 16)
}} finally {{
    if ($document -ne $null) {{
        try {{
            $document.Close(0)
        }} catch {{
        }}
    }}
    if ($word -ne $null) {{
        try {{
            $word.Quit()
        }} catch {{
        }}
    }}
}}
"""
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 and not docx_path.exists():
        details = (result.stderr or result.stdout or f"PowerShell exited with code {result.returncode}").strip()
        raise RuntimeError(details)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a Markdown mémoire to DOCX.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source_path = args.source.resolve()
    output_path = args.output.resolve()
    title = source_path.stem.replace("_", " ")

    markdown_text = source_path.read_text(encoding="utf-8")
    html_text = build_html(markdown_text, title)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as handle:
        html_path = Path(handle.name)
        handle.write(html_text)

    try:
        convert_html_to_docx(html_path, output_path)
    finally:
        html_path.unlink(missing_ok=True)

    print(output_path)


if __name__ == "__main__":
    main()