from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from common import STATUS_LABEL

# Legenda do Checklist: azul = atende | verde = parcialmente | amarelo = não atende
COLORS = {"A": colors.HexColor("#CFE2FF"), "AP": colors.HexColor("#D1E7DD"), "NA": colors.HexColor("#FFF3CD"),
          "NSA": colors.HexColor("#E9ECEF"), "-": colors.white}


def export_results_to_pdf(sections, pdf_path=None, manual=None, meta=None):
    st = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=st["Normal"], fontName="Helvetica", fontSize=8.5, leading=10.5)
    head = ParagraphStyle("h", parent=st["Normal"], fontName="Helvetica-Bold", fontSize=9.5)
    pdf_path = Path(pdf_path or f"relatorio_reci_checker_{datetime.now():%Y%m%d_%H%M%S}.pdf")
    doc = SimpleDocTemplate(pdf_path.as_posix(), pagesize=A4, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
    el = [Paragraph("Relatório de Verificação de Manuscrito – RECI", st["Title"])]
    if meta:
        el.append(Paragraph(escape(" | ".join(f"{k}: {v}" for k, v in meta.items())), body))
    el.append(Paragraph("Legenda: <font backColor='#CFE2FF'>&nbsp;A = Atende&nbsp;</font> "
                        "<font backColor='#D1E7DD'>&nbsp;AP = Atende parcialmente&nbsp;</font> "
                        "<font backColor='#FFF3CD'>&nbsp;NA = Não atende&nbsp;</font> "
                        "&nbsp;NSA = Não se aplica&nbsp; - = Não verificado (conferir manualmente)", body))
    el.append(Spacer(1, 8))

    rows, styles = [["Item", "Descrição", "Status", "Comentários"]], []
    styles += [("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    for name, rs in sections:
        rows.append([Paragraph(escape(name), head), "", "", ""])
        r = len(rows) - 1
        styles += [("SPAN", (0, r), (-1, r)), ("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F1F3F5"))]
        for x in rs:
            rows.append([str(x["item"]), Paragraph(escape(str(x["description"])), body), x["status"],
                         Paragraph(escape(str(x["comments"])), body)])
            styles.append(("BACKGROUND", (2, len(rows) - 1), (2, len(rows) - 1), COLORS.get(x["status"], colors.white)))
    if manual:
        rows.append([Paragraph("VERIFICAÇÃO MANUAL (não automatizável)", head), "", "", ""])
        r = len(rows) - 1
        styles += [("SPAN", (0, r), (-1, r)), ("BACKGROUND", (0, r), (-1, r), colors.HexColor("#F1F3F5"))]
        for m in manual:
            rows.append(["", Paragraph(escape(m), body), "-", ""])
    t = Table(rows, colWidths=[30, 230, 32, 250], repeatRows=1)
    t.setStyle(TableStyle(styles + [("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                                    ("ALIGN", (0, 0), (0, -1), "CENTER"), ("ALIGN", (2, 0), (2, -1), "CENTER"),
                                    ("FONTSIZE", (0, 0), (-1, -1), 8.5)]))
    el.append(t)
    doc.build(el)
    print(f"\nPDF gerado em: {pdf_path.resolve()}")
    return pdf_path
