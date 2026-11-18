"""
ReportLab Academic PDF Compiler.
Enforces exact university formatting:
- 1-inch margins (72 pt) on all sides
- A4 Portrait
- Times New Roman 12pt, Justified alignment
- Academic metadata table
- Dynamic 'Page X of Y' pagination
- Elegant academic code callouts (NO heavy terminal boxes)
- Table parsing, heading normalization, and ASCII art filtering
- File size < 2 MB
"""
from typing import List, Dict, Any
from pathlib import Path
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Dynamic two-pass canvas to compute and draw 'Page X of Y' in footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Times-Roman", 10)
        self.setFillColor(colors.HexColor("#333333"))
        
        page_width, page_height = A4
        left_margin = 72
        right_margin = page_width - 72
        
        # Running header on subsequent pages
        if self._pageNumber > 1:
            self.drawString(left_margin, page_height - 50, "Internal Assignment Submission")
            self.setStrokeColor(colors.HexColor("#D1D5DB"))
            self.setLineWidth(0.5)
            self.line(left_margin, page_height - 54, right_margin, page_height - 54)
            
        # Running footer
        footer_y = 45
        self.setStrokeColor(colors.HexColor("#D1D5DB"))
        self.setLineWidth(0.5)
        self.line(left_margin, footer_y + 12, right_margin, footer_y + 12)
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(right_margin, footer_y, page_str)
        self.restoreState()


def is_ascii_diagram_line(line: str) -> bool:
    """Detects if a single line belongs to an ASCII art box diagram."""
    line_clean = line.strip()
    if not line_clean:
        return False
    # Pure box boundary line
    if re.match(r'^[\+\-\|\=\:\#\s]{3,}$', line_clean):
        return True
    # Box interior with multiple pipes and minimal text
    if line_clean.startswith('|') or line_clean.startswith('+'):
        box_chars = sum(1 for c in line_clean if c in '+-|:=_# ')
        if len(line_clean) > 0 and (box_chars / len(line_clean)) > 0.55:
            return True
    return False


def clean_inline_formatting(text: str) -> str:
    """Safely escapes HTML and formats bold, italic, inline code, and math."""
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # Bold **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Italic *text* or _text_
    text = re.sub(r'(?<!\w)\*(.*?)\*(?!\w)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!\w)_(.*?)_(?!\w)', r'<i>\1</i>', text)
    # Inline code `text` -> bold text without backticks
    text = re.sub(r'`(.*?)`', r'<b>\1</b>', text)
    # LaTeX math $$...$$ or $...$ -> italic text
    text = re.sub(r'\$\$(.*?)\$\$', r'<i>\1</i>', text)
    text = re.sub(r'\$(.*?)\$', r'<i>\1</i>', text)
    return text


def parse_markdown_table(table_lines: List[str], col_width_total: float, subheading_style, body_style):
    """Parses a markdown table into a ReportLab Table."""
    data = []
    for line in table_lines:
        line_clean = line.strip()
        if re.match(r'^\|?[\s\-:|]+\|?$', line_clean):
            continue  # Separator line like |---|---|
        cells = [c.strip() for c in line_clean.strip('|').split('|')]
        if cells:
            data.append(cells)
    
    if not data or len(data) < 1:
        return None
    
    num_cols = max(len(row) for row in data)
    col_width = col_width_total / num_cols
    
    formatted_data = []
    for row_idx, row in enumerate(data):
        while len(row) < num_cols:
            row.append("")
        row_cells = []
        for cell in row:
            clean_c = clean_inline_formatting(cell)
            if row_idx == 0:
                p = Paragraph(f"<b>{clean_c}</b>", subheading_style)
            else:
                p = Paragraph(clean_c, body_style)
            row_cells.append(p)
        formatted_data.append(row_cells)
        
    t = Table(formatted_data, colWidths=[col_width] * num_cols)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def parse_answer_to_flowables(raw_ans: str, usable_w: float, styles: Any):
    """
    Parses raw LLM answer text into academic ReportLab flowables:
    - Normalizes markdown headings to clean bold subheadings
    - Filters out ASCII art box drawings
    - Formats code blocks as subtle academic callouts instead of terminal boxes
    - Formats bullet points and numbered lists with clean indentation
    - Converts markdown tables into clean university tables
    """
    flowables = []
    
    body_style = styles['AcademicBody']
    subheading_style = styles['AcademicSubheading']
    bullet_style = styles['AcademicBullet']
    code_style = styles['AcademicCode']
    
    # Split code blocks first
    parts = re.split(r'(```[\s\S]*?```)', raw_ans)
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        if part.startswith("```"):
            code_content = re.sub(r'^```[a-zA-Z0-9_-]*\n?', '', part)
            code_content = re.sub(r'```$', '', code_content).strip()
            
            # Check if this code block is actually an ASCII art diagram
            lines = code_content.split('\n')
            ascii_count = sum(1 for l in lines if is_ascii_diagram_line(l))
            if len(lines) >= 2 and (ascii_count / len(lines)) > 0.5:
                # Skip ASCII art box drawings
                continue
                
            # Render elegant academic code callout (clean slate accent line, subtle off-white background)
            code_escaped = code_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            code_html = code_escaped.replace('\n', '<br/>').replace(' ', '&nbsp;')
            
            p = Paragraph(code_html, code_style)
            t = Table([[p]], colWidths=[usable_w])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ('LINEBEFORE', (0, 0), (0, -1), 2.5, colors.HexColor("#475569")),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            flowables.append(Spacer(1, 4))
            flowables.append(t)
            flowables.append(Spacer(1, 6))
        else:
            # Process text line by line with paragraph and table buffering
            lines = part.split('\n')
            p_buffer = []
            table_buffer = []
            
            def flush_p_buffer():
                if p_buffer:
                    full_p = " ".join(p_buffer).strip()
                    if full_p:
                        clean_p = clean_inline_formatting(full_p)
                        flowables.append(Paragraph(clean_p, body_style))
                    p_buffer.clear()
                    
            def flush_table_buffer():
                if table_buffer:
                    t = parse_markdown_table(table_buffer, usable_w, subheading_style, body_style)
                    if t:
                        flowables.append(Spacer(1, 4))
                        flowables.append(t)
                        flowables.append(Spacer(1, 6))
                    table_buffer.clear()

            for line in lines:
                line_str = line.strip()
                
                # Check for table line
                if line_str.startswith('|') and line_str.endswith('|') and not is_ascii_diagram_line(line_str):
                    flush_p_buffer()
                    table_buffer.append(line_str)
                    continue
                else:
                    flush_table_buffer()
                    
                # Empty line: paragraph separator
                if not line_str:
                    flush_p_buffer()
                    continue
                    
                # Check for ASCII art diagram line
                if is_ascii_diagram_line(line_str):
                    flush_p_buffer()
                    continue
                    
                # Markdown headings: ### Title, ## Title, # Title
                if re.match(r'^#{1,6}\s+', line_str):
                    flush_p_buffer()
                    clean_head = re.sub(r'^#{1,6}\s+', '', line_str).strip()
                    clean_head = clean_inline_formatting(clean_head)
                    flowables.append(Paragraph(clean_head, subheading_style))
                # Standalone bold header: **1. Introduction**
                elif re.match(r'^\*\*[0-9A-Za-z\.\s\-:]+\*\*$', line_str):
                    flush_p_buffer()
                    clean_head = clean_inline_formatting(line_str)
                    flowables.append(Paragraph(clean_head, subheading_style))
                # Bullet items: * or - or •
                elif re.match(r'^[\*\-•]\s+', line_str):
                    flush_p_buffer()
                    bullet_body = re.sub(r'^[\*\-•]\s+', '', line_str).strip()
                    clean_b = clean_inline_formatting(bullet_body)
                    flowables.append(Paragraph(f"&bull; &nbsp; {clean_b}", bullet_style))
                # Numbered list items: 1. or 2.
                elif re.match(r'^[0-9]+\.\s+', line_str):
                    flush_p_buffer()
                    num_prefix = re.match(r'^[0-9]+\.', line_str).group(0)
                    num_body = re.sub(r'^[0-9]+\.\s+', '', line_str).strip()
                    clean_n = clean_inline_formatting(num_body)
                    flowables.append(Paragraph(f"<b>{num_prefix}</b> &nbsp; {clean_n}", bullet_style))
                else:
                    # Regular text line belonging to a paragraph
                    p_buffer.append(line_str)
                    
            flush_p_buffer()
            flush_table_buffer()
            
    return flowables


def compile_final_pdf(
    output_path: Path,
    metadata: Dict[str, str],
    answers: List[Dict[str, Any]]
) -> str:
    """Compiles the structured answers into a university-formatted PDF."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=72,
        rightMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    usable_width = A4[0] - 144
    sample_styles = getSampleStyleSheet()

    custom_styles = {
        'AcademicBody': ParagraphStyle(
            'AcademicBody',
            parent=sample_styles['Normal'],
            fontName='Times-Roman',
            fontSize=12,
            leading=16,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            textColor=colors.HexColor("#111111")
        ),
        'AcademicSubheading': ParagraphStyle(
            'AcademicSubheading',
            parent=sample_styles['Normal'],
            fontName='Times-Bold',
            fontSize=12,
            leading=16,
            alignment=TA_LEFT,
            spaceBefore=11,
            spaceAfter=4,
            textColor=colors.HexColor("#000000")
        ),
        'AcademicBullet': ParagraphStyle(
            'AcademicBullet',
            parent=sample_styles['Normal'],
            fontName='Times-Roman',
            fontSize=12,
            leading=16,
            alignment=TA_JUSTIFY,
            leftIndent=16,
            firstLineIndent=-10,
            spaceAfter=3,
            textColor=colors.HexColor("#111111")
        ),
        'AcademicCode': ParagraphStyle(
            'AcademicCode',
            parent=sample_styles['Normal'],
            fontName='Courier',
            fontSize=8.5,
            leading=11.5,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1E293B"),
        )
    }

    question_style = ParagraphStyle(
        'QuestionHeader',
        parent=sample_styles['Normal'],
        fontName='Times-Bold',
        fontSize=12,
        leading=16,
        alignment=TA_LEFT,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#000000")
    )

    title_style = ParagraphStyle(
        'HeaderTitle',
        parent=sample_styles['Normal'],
        fontName='Times-Bold',
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'HeaderSubtitle',
        parent=sample_styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    story = []

    # Title & Header
    inst_name = metadata.get("institution", "Centre for Distance & Online Education, Manipal University Jaipur")
    story.append(Paragraph(inst_name, subtitle_style))
    story.append(Paragraph("INTERNAL ASSIGNMENT", title_style))
    story.append(Spacer(1, 4))

    # Metadata Table
    table_data = [
        [
            Paragraph("<b>SESSION</b>", sample_styles['Normal']),
            Paragraph(metadata.get("session", "JULY 2026"), sample_styles['Normal'])
        ],
        [
            Paragraph("<b>PROGRAM</b>", sample_styles['Normal']),
            Paragraph(metadata.get("program", "MASTER OF COMPUTER APPLICATIONS (MCA)"), sample_styles['Normal'])
        ],
        [
            Paragraph("<b>SEMESTER</b>", sample_styles['Normal']),
            Paragraph(metadata.get("semester", "3"), sample_styles['Normal'])
        ],
        [
            Paragraph("<b>COURSE CODE & NAME</b>", sample_styles['Normal']),
            Paragraph(metadata.get("course_code_name", "DCA7106 - Web Technologies"), sample_styles['Normal'])
        ],
        [
            Paragraph("<b>STUDENT INFO</b>", sample_styles['Normal']),
            Paragraph(metadata.get("student_info", "Learner Submission"), sample_styles['Normal'])
        ]
    ]

    meta_table = Table(table_data, colWidths=[160, usable_width - 160])
    meta_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.75, colors.HexColor("#222222")),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#F8F9FA")),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 10.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#333333"), spaceAfter=14))

    # Questions & Formatted Answers
    for item in answers:
        q_num = item.get("number", 1)
        q_text = item.get("question", "")
        marks = item.get("marks", 10)
        raw_ans = item.get("answer", "")

        q_heading = f"<b>Q{q_num}. {q_text} &nbsp;&nbsp;[{marks} Marks]</b>"
        story.append(Paragraph(q_heading, question_style))

        # Parse and format answer content
        answer_flowables = parse_answer_to_flowables(raw_ans, usable_width, custom_styles)
        story.extend(answer_flowables)
        story.append(Spacer(1, 12))

    doc.build(story, canvasmaker=NumberedCanvas)
    return str(output_path)
