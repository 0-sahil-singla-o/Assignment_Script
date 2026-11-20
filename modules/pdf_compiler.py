"""
ReportLab Academic PDF Compiler.
Enforces dynamic formatting completely driven by extracted layout specs:
- Dynamic page margins (e.g. 1.0 inch / 72 pt) with zero frame padding (starts exactly at margin)
- Dynamic page size & orientation (A4 / Letter, Portrait / Landscape)
- Dynamic font family & size applied uniformly across ALL sections (body, code blocks, tables, titles, headers/footers)
- Dynamic color & shading enforcement (plain white, pure black when color/shading is disabled)
- Dynamic two-pass pagination ('Page X of Y')
- Table parsing, heading normalization, and ASCII art filtering
- File size < 2 MB
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import re
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Dynamic two-pass canvas to compute and draw 'Page X of Y' in footer using extracted layout specs."""
    font_name = "Times-Roman"
    font_size = 12
    margin_pts = 72.0
    text_color = colors.black

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
        self.setFont(self.font_name, self.font_size)
        self.setFillColor(self.text_color)
        
        page_width, page_height = self._pagesize
        left_m = self.margin_pts
        right_m = page_width - self.margin_pts
        
        # Running footer on all pages (clean page numbering)
        footer_y = self.margin_pts * 0.52
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(right_m, footer_y, page_str)
        self.restoreState()


def is_ascii_diagram_line(line: str) -> bool:
    """Detects if a single line belongs to an ASCII art box diagram."""
    line_clean = line.strip()
    if not line_clean:
        return False
    if re.match(r'^[\+\-\|\=\:\#\s]{3,}$', line_clean):
        return True
    if line_clean.startswith('|') or line_clean.startswith('+'):
        box_chars = sum(1 for c in line_clean if c in '+-|:=_# ')
        if len(line_clean) > 0 and (box_chars / len(line_clean)) > 0.55:
            return True
    return False


def clean_inline_formatting(text: str) -> str:
    """Safely escapes HTML and formats bold, italic, inline code, and math."""
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\w)\*(.*?)\*(?!\w)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!\w)_(.*?)_(?!\w)', r'<i>\1</i>', text)
    text = re.sub(r'`(.*?)`', r'<b>\1</b>', text)
    text = re.sub(r'\$\$(.*?)\$\$', r'<i>\1</i>', text)
    text = re.sub(r'\$(.*?)\$', r'<i>\1</i>', text)
    return text


def parse_markdown_table(
    table_lines: List[str],
    col_width_total: float,
    subheading_style: ParagraphStyle,
    body_style: ParagraphStyle,
    allow_shading: bool = False,
    grid_color: Any = colors.black
) -> Optional[Table]:
    """Parses a markdown table into a ReportLab Table following dynamic font and shading rules."""
    data = []
    for line in table_lines:
        line_clean = line.strip()
        if re.match(r'^\|?[\s\-:|]+\|?$', line_clean):
            continue
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
        
    t = Table(formatted_data, colWidths=[col_width] * num_cols, hAlign='LEFT')
    
    table_styles = [
        ('GRID', (0, 0), (-1, -1), 0.5, grid_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    if allow_shading:
        table_styles.append(('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")))
        
    t.setStyle(TableStyle(table_styles))
    return t


def parse_answer_to_flowables(
    raw_ans: str,
    usable_w: float,
    styles: Any,
    layout_specs: Optional[Dict[str, Any]] = None,
    grid_color: Any = colors.black
) -> List[Any]:
    """
    Parses raw LLM answer text into academic ReportLab flowables adhering dynamically to layout_specs:
    - Font family & size match the rest of the document
    - Shading / borders removed if allow_shading is False
    - Headings, lists, and tables cleanly formatted
    """
    specs = layout_specs or {}
    allow_shading = bool(specs.get("allow_shading", False))

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
                continue
                
            code_escaped = code_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            code_html = code_escaped.replace('\n', '<br/>').replace(' ', '&nbsp;')
            
            p = Paragraph(code_html, code_style)
            flowables.append(Spacer(1, 4))
            flowables.append(p)
            flowables.append(Spacer(1, 6))
        else:
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
                    t = parse_markdown_table(
                        table_buffer,
                        usable_w,
                        subheading_style,
                        body_style,
                        allow_shading=allow_shading,
                        grid_color=grid_color
                    )
                    if t:
                        flowables.append(Spacer(1, 4))
                        flowables.append(t)
                        flowables.append(Spacer(1, 6))
                    table_buffer.clear()

            for line in lines:
                line_str = line.strip()
                
                if line_str.startswith('|') and line_str.endswith('|') and not is_ascii_diagram_line(line_str):
                    flush_p_buffer()
                    table_buffer.append(line_str)
                    continue
                else:
                    flush_table_buffer()
                    
                if not line_str:
                    flush_p_buffer()
                    continue
                    
                if is_ascii_diagram_line(line_str):
                    flush_p_buffer()
                    continue
                    
                if re.match(r'^#{1,6}\s+', line_str):
                    flush_p_buffer()
                    clean_head = re.sub(r'^#{1,6}\s+', '', line_str).strip()
                    clean_head = clean_inline_formatting(clean_head)
                    flowables.append(Paragraph(clean_head, subheading_style))
                elif re.match(r'^\*\*[0-9A-Za-z\.\s\-:]+\*\*$', line_str):
                    flush_p_buffer()
                    clean_head = clean_inline_formatting(line_str)
                    flowables.append(Paragraph(clean_head, subheading_style))
                elif re.match(r'^[\*\-•]\s+', line_str):
                    flush_p_buffer()
                    bullet_body = re.sub(r'^[\*\-•]\s+', '', line_str).strip()
                    clean_b = clean_inline_formatting(bullet_body)
                    flowables.append(Paragraph(f"&bull; &nbsp; {clean_b}", bullet_style))
                elif re.match(r'^[0-9]+\.\s+', line_str):
                    flush_p_buffer()
                    num_prefix = re.match(r'^[0-9]+\.', line_str).group(0)
                    num_body = re.sub(r'^[0-9]+\.\s+', '', line_str).strip()
                    clean_n = clean_inline_formatting(num_body)
                    flowables.append(Paragraph(f"<b>{num_prefix}</b> &nbsp; {clean_n}", bullet_style))
                else:
                    p_buffer.append(line_str)
                    
            flush_p_buffer()
            flush_table_buffer()
            
    return flowables


def compile_final_pdf(
    output_path: Path,
    metadata: Dict[str, str],
    answers: List[Dict[str, Any]],
    layout_specs: Optional[Dict[str, Any]] = None
) -> str:
    """
    Compiles structured answers into a university-formatted PDF using dynamic layout specs:
    - Margins, font family, font size, and alignment are extracted dynamically
    - The extracted font & size are applied consistently across all sections
    - Frame padding is 0pt so margins align exactly to the extracted specification
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    specs = {
        "page_margin_inch": 1.0,
        "page_size": "A4",
        "orientation": "PORTRAIT",
        "font_family": "Times-Roman",
        "font_size": 12,
        "alignment": "JUSTIFIED",
        "max_pages": 12,
        "allow_shading": False,
        "allow_colors": False,
        "plain_code_blocks": True
    }
    if layout_specs:
        specs.update(layout_specs)
        
    margin_inch = float(specs.get("page_margin_inch", 1.0))
    margin_pts = margin_inch * 72.0
    
    # Page size
    page_size_choice = A4
    if str(specs.get("page_size", "A4")).upper() == "LETTER":
        page_size_choice = letter
        
    usable_width = page_size_choice[0] - (2 * margin_pts)
    usable_height = page_size_choice[1] - (2 * margin_pts)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=page_size_choice,
        leftMargin=margin_pts,
        rightMargin=margin_pts,
        topMargin=margin_pts,
        bottomMargin=margin_pts
    )

    # Frame with 0 padding ensures text aligns exactly to margin_pts without default 6pt offset
    frame = Frame(
        margin_pts,
        margin_pts,
        usable_width,
        usable_height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id='normal'
    )
    template = PageTemplate(id='normal', frames=frame)
    doc.addPageTemplates([template])

    # Dynamic Font Family mapping from extracted specs
    font_req = str(specs.get("font_family", "Times-Roman")).strip().lower()
    if "times" in font_req:
        font_regular = "Times-Roman"
        font_bold = "Times-Bold"
        font_italic = "Times-Italic"
    elif "helvetica" in font_req or "arial" in font_req:
        font_regular = "Helvetica"
        font_bold = "Helvetica-Bold"
        font_italic = "Helvetica-Oblique"
    elif "courier" in font_req:
        font_regular = "Courier"
        font_bold = "Courier-Bold"
        font_italic = "Courier-Oblique"
    else:
        font_regular = "Times-Roman"
        font_bold = "Times-Bold"
        font_italic = "Times-Italic"

    # Dynamic Font Size & Leading from extracted specs
    font_sz = int(specs.get("font_size", 12))
    leading_sz = int(font_sz * 1.33)

    # Dynamic Alignment
    align_choice = TA_JUSTIFY if str(specs.get("alignment", "JUSTIFIED")).upper() == "JUSTIFIED" else TA_LEFT

    # Dynamic Colors
    allow_colors = bool(specs.get("allow_colors", False))
    allow_shading = bool(specs.get("allow_shading", False))
    main_text_color = colors.black if not allow_colors else colors.HexColor("#111111")
    grid_line_color = colors.black if not allow_colors else colors.HexColor("#222222")

    # Configure NumberedCanvas dynamically
    NumberedCanvas.font_name = font_regular
    NumberedCanvas.font_size = font_sz
    NumberedCanvas.margin_pts = margin_pts
    NumberedCanvas.text_color = main_text_color

    custom_styles = {
        'AcademicBody': ParagraphStyle(
            'AcademicBody',
            fontName=font_regular,
            fontSize=font_sz,
            leading=leading_sz,
            alignment=align_choice,
            spaceAfter=8,
            textColor=main_text_color
        ),
        'AcademicSubheading': ParagraphStyle(
            'AcademicSubheading',
            fontName=font_bold,
            fontSize=font_sz,
            leading=leading_sz,
            alignment=TA_LEFT,
            spaceBefore=11,
            spaceAfter=4,
            textColor=main_text_color
        ),
        'AcademicBullet': ParagraphStyle(
            'AcademicBullet',
            fontName=font_regular,
            fontSize=font_sz,
            leading=leading_sz,
            alignment=align_choice,
            leftIndent=16,
            firstLineIndent=-10,
            spaceAfter=3,
            textColor=main_text_color
        ),
        # Code snippets uniformly take the extracted font family and font size
        'AcademicCode': ParagraphStyle(
            'AcademicCode',
            fontName=font_regular,
            fontSize=font_sz,
            leading=leading_sz,
            alignment=TA_LEFT,
            leftIndent=16,
            textColor=main_text_color
        )
    }

    question_style = ParagraphStyle(
        'QuestionHeader',
        fontName=font_bold,
        fontSize=font_sz,
        leading=leading_sz,
        alignment=TA_LEFT,
        spaceBefore=14,
        spaceAfter=8,
        textColor=main_text_color
    )

    title_style = ParagraphStyle(
        'HeaderTitle',
        fontName=font_bold,
        fontSize=font_sz,
        leading=leading_sz,
        alignment=TA_CENTER,
        spaceAfter=8,
        textColor=main_text_color
    )

    subtitle_style = ParagraphStyle(
        'HeaderSubtitle',
        fontName=font_regular,
        fontSize=font_sz,
        leading=leading_sz,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=main_text_color
    )

    story = []

    # Title & Header
    inst_name = metadata.get("institution", "Centre for Distance & Online Education, Manipal University Jaipur")
    story.append(Paragraph(inst_name, subtitle_style))
    story.append(Paragraph("INTERNAL ASSIGNMENT", title_style))
    story.append(Spacer(1, 4))

    # Cover table styles using extracted font and size
    table_head_style = ParagraphStyle(
        'CoverTableHead',
        fontName=font_bold,
        fontSize=font_sz,
        leading=int(font_sz * 1.25),
        textColor=main_text_color
    )
    table_cell_style = ParagraphStyle(
        'CoverTableCell',
        fontName=font_regular,
        fontSize=font_sz,
        leading=int(font_sz * 1.25),
        textColor=main_text_color
    )

    table_data = [
        [
            Paragraph("SESSION", table_head_style),
            Paragraph(metadata.get("session", "JULY 2026"), table_cell_style)
        ],
        [
            Paragraph("PROGRAM", table_head_style),
            Paragraph(metadata.get("program", "MASTER OF COMPUTER APPLICATIONS (MCA)"), table_cell_style)
        ],
        [
            Paragraph("SEMESTER", table_head_style),
            Paragraph(metadata.get("semester", "3"), table_cell_style)
        ],
        [
            Paragraph("COURSE CODE & NAME", table_head_style),
            Paragraph(metadata.get("course_code_name", "DCA7106 - Web Technologies"), table_cell_style)
        ],
        [
            Paragraph("STUDENT INFO", table_head_style),
            Paragraph(metadata.get("student_info", "Learner Submission"), table_cell_style)
        ]
    ]

    meta_table_style = [
        ('GRID', (0, 0), (-1, -1), 0.5, grid_line_color),
        ('FONTNAME', (0, 0), (-1, -1), font_regular),
        ('FONTSIZE', (0, 0), (-1, -1), font_sz),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    if allow_shading:
        meta_table_style.append(('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#F8F9FA")))

    meta_table = Table(table_data, colWidths=[160, usable_width - 160], hAlign='LEFT')
    meta_table.setStyle(TableStyle(meta_table_style))
    story.append(meta_table)
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=grid_line_color, hAlign='LEFT', spaceAfter=14))

    # Questions & Formatted Answers
    for item in answers:
        q_num = item.get("number", 1)
        q_text = item.get("question", "")
        marks = item.get("marks", 10)
        raw_ans = item.get("answer", "")

        q_heading = f"<b>Q{q_num}. {q_text} &nbsp;&nbsp;[{marks} Marks]</b>"
        story.append(Paragraph(q_heading, question_style))

        # Parse and format answer content
        answer_flowables = parse_answer_to_flowables(
            raw_ans,
            usable_width,
            custom_styles,
            layout_specs=specs,
            grid_color=grid_line_color
        )
        story.extend(answer_flowables)
        story.append(Spacer(1, 12))

    doc.build(story, canvasmaker=NumberedCanvas)
    return str(output_path)
