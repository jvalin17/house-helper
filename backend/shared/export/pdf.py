"""PDF exporter — converts markdown to HTML, then to PDF via WeasyPrint."""

import markdown
from weasyprint import HTML

BASE_CSS = """
body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    max-width: 800px;
    margin: 0 auto;
    padding: 40px;
    color: #333;
}
h1 { font-size: 22pt; margin-bottom: 4px; color: #1a1a1a; }
h2 { font-size: 14pt; margin-top: 20px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
h3 { font-size: 12pt; margin-bottom: 2px; }
ul { padding-left: 20px; }
"""


class PdfExporter:
    def export(self, content: str, metadata: dict) -> bytes:
        html_body = markdown.markdown(content)
        full_html = f"""
        <html>
        <head><style>{BASE_CSS}</style></head>
        <body>{html_body}</body>
        </html>
        """
        return HTML(string=full_html).write_pdf()

    def format_name(self) -> str:
        return "pdf"
