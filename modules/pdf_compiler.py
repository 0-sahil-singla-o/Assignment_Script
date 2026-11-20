"""
ReportLab Academic PDF Compiler.
Enforces dynamic university formatting based on extracted layout specifications:
- Page Geometry: Margins (uniform or directional), Page size (A4, Letter, Legal), Orientation
- Typography: Font family (Arial/Helvetica, Times-Roman, Courier), Font size, Line spacing (leading)
- Color: Dynamic font color (Hex code e.g. #1F3864, #000000)
- Alignment: Left, Justified, Center
- Table parsing, heading normalization, and ASCII art filtering
- Dynamic 'Page X of Y' pagination
- File size < 2 MB
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import re
import os

from reportlab.lib.pagesizes import A4, letter, legal, landscape
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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register TrueType Arial if running on Windows
def register_system_fonts():
    registered = pdfmetrics.getRegisteredFontNames()
    if os.path.exists("C:/Windows/Fonts/arial.ttf") and "Arial" not in registered:
        try:
            pdfmetrics.registerFont(TTFont("Arial", "C:/Windows/Fonts/arial.ttf"))
            if os.path.exists("C:/Windows/Fonts/arialbd.ttf"):
                pdfmetrics.registerFont(TTFont("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"))
            if os.path.exists("C:/Windows/Fonts/ariali.ttf"):
                pdfmetrics.registerFont(TTFont("Arial-Italic", "C:/Windows/Fonts/ariali.ttf"))
        except Exception as e:
            print(f"Font registration notice: {e}")

register_system_fonts()


class NumberedCanvas(canvas.Canvas):
    """Dynamic two-pass canvas to compute and draw page numbering and headers."""
    font_name = "Times-Roman"
    font_size = 11
    left_margin_pts = 72.0
    right_margin_pts = 72.0
    top_margin_pts = 72.0
    bottom_margin_pts = 72.0
    text_color = colors.HexColor("#000000")
    page_format = "Page X of Y"
    header_rule_line = True
    page_position = "BOTTOM_RIGHT"

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
        self.setFont(self.font_name, max(9, self.font_size - 1))
        self.setFillColor(self.text_color)
        
        page_width, page_height = self._pagesize
        left_m = self.left_margin_pts
        right_m = page_width - self.right_margin_pts
        
        # Running header on subsequent pages (page 2+)
        if self._pageNumber > 1:
            header_y = page_height - (self.top_margin_pts * 0.55)
            self.drawString(left_m, header_y, "Internal Assignment Submission")
            if self.header_rule_line:
                self.setStrokeColor(self.text_color)
                self.setLineWidth(0.4)
                self.line(left_m, header_y - 4, right_m, header_y - 4)
            
        # Running footer
        footer_y = self.bottom_margin_pts * 0.5
        if "x / y" in self.page_format.lower():
            page_str = f"{self._pageNumber} / {page_count}"
        elif "page x" == self.page_format.lower().strip():
            page_str = f"Page {self._pageNumber}"
        else:
            page_str = f"Page {self._pageNumber} of {page_count}"
            
        if self.page_position == "BOTTOM_CENTER":
            self.drawCentredString(page_width / 2.0, footer_y, page_str)
        else:
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
    grid_color: Any = colors.black,
    table_borders: str = "GRID"
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
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    
    if table_borders == "SIMPLE_LINES":
        table_styles.extend([
            ('LINEABOVE', (0, 0), (-1, 0), 1.0, grid_color),
            ('LINEBELOW', (0, 0), (-1, 0), 0.75, grid_color),
            ('LINEBELOW', (0, -1), (-1, -1), 1.0, grid_color),
        ])
    else:
        table_styles.append(('GRID', (0, 0), (-1, -1), 0.5, grid_color))
        
    if allow_shading:
        table_styles.append(('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")))
        
    t.setStyle(TableStyle(table_styles))
    return t


def parse_answer_to_flowables(
    raw_ans: str,
    usable_w: float,
    styles: Dict[str, ParagraphStyle],
    layout_specs: Optional[Dict[str, Any]] = None,
    grid_color: Any = colors.black
) -> List[Any]:
    """Parses raw answer text into flowables respecting dynamic styling specs."""
    flowables = []
    specs = layout_specs or {}
    
    body_style = styles['AcademicBody']
    subheading_style = styles['AcademicSubheading']
    bullet_style = styles['AcademicBullet']
    code_style = styles['AcademicCode']
    
    allow_shading = bool(specs.get("allow_shading", False))
    plain_code = bool(specs.get("plain_code_blocks", True))
    table_borders = str(specs.get("table_borders", "GRID")).upper()
    
    parts = re.split(r'(```[\s\S]*?```)', raw_ans)
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        if part.startswith("```"):
            code_content = re.sub(r'^```[a-zA-Z0-9_-]*\n?', '', part)
            code_content = re.sub(r'```$', '', code_content).strip()
            
            lines = code_content.split('\n')
            ascii_count = sum(1 for l in lines if is_ascii_diagram_line(l))
            if len(lines) >= 2 and (ascii_count / len(lines)) > 0.5:
                continue
                
            code_escaped = code_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            code_html = code_escaped.replace('\n', '<br/>').replace(' ', '&nbsp;')
            p = Paragraph(code_html, code_style)
            
            if plain_code or not allow_shading:
                # Plain, clean, unshaded textbook code block
                flowables.append(Spacer(1, 4))
                flowables.append(p)
                flowables.append(Spacer(1, 6))
            else:
                # Shaded callout block
                t = Table([[p]], colWidths=[usable_w], hAlign='LEFT')
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ('LINEBEFORE', (0, 0), (0, -1), 2.0, colors.HexColor("#475569")),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                flowables.append(Spacer(1, 4))
                flowables.append(t)
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
                        grid_color=grid_color,
                        table_borders=table_borders
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
    Compiles structured answers into a university-formatted PDF using extracted dynamic layout specs:
    - Page Geometry: Margins (uniform or directional), Page size (A4, Letter, Legal), Orientation
    - Typography: Font family (Arial TTF/Helvetica, Times-Roman, etc.), Font size, Line spacing
    - Font Color: Dynamic hex color (e.g. #1F3864 Dark Blue) applied across document
    - Alignment: Left, Justified, Center
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    specs = {
        "page_size": "A4",
        "orientation": "PORTRAIT",
        "page_margin_inch": 1.0,
        "top_margin_inch": None,
        "bottom_margin_inch": None,
        "left_margin_inch": None,
        "right_margin_inch": None,
        "max_pages": 12,
        "max_file_size_mb": 2.0,
        "font_family": "Times-Roman",
        "font_size": 12,
        "font_color": "#000000",
        "line_spacing": 1.33,
        "alignment": "JUSTIFIED",
        "paragraph_spacing_pt": 8,
        "heading_font_family": None,
        "heading_font_size": 13,
        "heading_font_color": None,
        "allow_color_images": True,
        "allow_text_highlighting": False,
        "allow_shading": False,
        "plain_code_blocks": True,
        "table_borders": "GRID",
        "page_numbering_format": "Page X of Y",
        "page_number_position": "BOTTOM_RIGHT",
        "header_rule_line": True
    }
    if layout_specs:
        specs.update(layout_specs)
        
    # 1. Page Geometry Margins
    base_m = float(specs.get("page_margin_inch", 1.0))
    left_m_pts = float(specs.get("left_margin_inch") or base_m) * 72.0
    right_m_pts = float(specs.get("right_margin_inch") or base_m) * 72.0
    top_m_pts = float(specs.get("top_margin_inch") or base_m) * 72.0
    bottom_m_pts = float(specs.get("bottom_margin_inch") or base_m) * 72.0
    
    # 2. Page Size & Orientation
    p_size = str(specs.get("page_size", "A4")).upper().strip()
    if p_size in ["LETTER", "US LETTER"]:
        page_size_choice = letter
    elif p_size == "LEGAL":
        page_size_choice = legal
    else:
        page_size_choice = A4
        
    if str(specs.get("orientation", "PORTRAIT")).upper().strip() == "LANDSCAPE":
        page_size_choice = landscape(page_size_choice)
        
    usable_width = page_size_choice[0] - (left_m_pts + right_m_pts)
    usable_height = page_size_choice[1] - (top_m_pts + bottom_m_pts)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=page_size_choice,
        leftMargin=left_m_pts,
        rightMargin=right_m_pts,
        topMargin=top_m_pts,
        bottomMargin=bottom_m_pts
    )

    frame = Frame(
        left_m_pts,
        bottom_m_pts,
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

    # 3. Dynamic Font Family mapping
    font_req = str(specs.get("font_family", "Times-Roman")).strip().lower()
    registered = pdfmetrics.getRegisteredFontNames()
    if "arial" in font_req:
        if "Arial" in registered and "Arial-Bold" in registered:
            font_regular = "Arial"
            font_bold = "Arial-Bold"
            font_italic = "Arial-Italic" if "Arial-Italic" in registered else "Arial"
        else:
            font_regular = "Helvetica"
            font_bold = "Helvetica-Bold"
            font_italic = "Helvetica-Oblique"
    elif "helvetica" in font_req:
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

    # Heading font family
    heading_font_req = specs.get("heading_font_family")
    if heading_font_req:
        h_req = str(heading_font_req).lower()
        if "arial" in h_req:
            heading_font = "Arial-Bold" if "Arial-Bold" in registered else "Helvetica-Bold"
        else:
            heading_font = font_bold
    else:
        heading_font = font_bold

    # 4. Font Size & Line Spacing
    font_sz = float(specs.get("font_size", 12))
    line_spacing_mult = float(specs.get("line_spacing", 1.33))
    leading_sz = font_sz * line_spacing_mult
    para_spacing_pt = float(specs.get("paragraph_spacing_pt", 8))

    heading_sz = float(specs.get("heading_font_size", font_sz + 1))
    heading_leading = heading_sz * line_spacing_mult

    # 5. Dynamic Colors
    raw_color = str(specs.get("font_color", "#000000")).strip()
    try:
        main_text_color = colors.HexColor(raw_color)
    except Exception:
        main_text_color = colors.HexColor("#000000")
        
    raw_h_color = specs.get("heading_font_color")
    if raw_h_color:
        try:
            heading_text_color = colors.HexColor(str(raw_h_color).strip())
        except Exception:
            heading_text_color = main_text_color
    else:
        heading_text_color = main_text_color

    grid_line_color = main_text_color

    # 6. Alignment
    align_req = str(specs.get("alignment", "JUSTIFIED")).upper().strip()
    if align_req == "LEFT":
        align_choice = TA_LEFT
    elif align_req == "CENTER":
        align_choice = TA_CENTER
    else:
        align_choice = TA_JUSTIFY

    # Configure NumberedCanvas dynamically
    NumberedCanvas.font_name = font_regular
    NumberedCanvas.font_size = int(font_sz)
    NumberedCanvas.left_margin_pts = left_m_pts
    NumberedCanvas.right_margin_pts = right_m_pts
    NumberedCanvas.top_margin_pts = top_m_pts
    NumberedCanvas.bottom_margin_pts = bottom_m_pts
    NumberedCanvas.text_color = main_text_color
    NumberedCanvas.page_format = str(specs.get("page_numbering_format", "Page X of Y"))
    NumberedCanvas.page_position = str(specs.get("page_number_position", "BOTTOM_RIGHT"))
    NumberedCanvas.header_rule_line = bool(specs.get("header_rule_line", True))

    custom_styles = {
        'AcademicBody': ParagraphStyle(
            'AcademicBody',
            fontName=font_regular,
            fontSize=font_sz,
            leading=leading_sz,
            alignment=align_choice,
            spaceAfter=para_spacing_pt,
            textColor=main_text_color
        ),
        'AcademicSubheading': ParagraphStyle(
            'AcademicSubheading',
            fontName=heading_font,
            fontSize=heading_sz,
            leading=heading_leading,
            alignment=TA_LEFT,
            spaceBefore=11,
            spaceAfter=4,
            textColor=heading_text_color
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
        fontName=heading_font,
        fontSize=heading_sz,
        leading=heading_leading,
        alignment=TA_LEFT,
        spaceBefore=14,
        spaceAfter=8,
        textColor=heading_text_color
    )

    title_style = ParagraphStyle(
        'HeaderTitle',
        fontName=heading_font,
        fontSize=heading_sz + 3,
        leading=heading_leading + 4,
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

    # Cover table styles using dynamic font and color
    table_head_style = ParagraphStyle(
        'CoverTableHead',
        fontName=font_bold,
        fontSize=font_sz,
        leading=leading_sz,
        textColor=main_text_color
    )
    table_cell_style = ParagraphStyle(
        'CoverTableCell',
        fontName=font_regular,
        fontSize=font_sz,
        leading=leading_sz,
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

    allow_shading = bool(specs.get("allow_shading", False))
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
