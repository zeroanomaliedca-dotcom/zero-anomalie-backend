
from datetime import datetime, date, time, timedelta, timezone
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo
import os

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from app.models.anomaly import Anomaly
from app.models.anomaly_photo import AnomalyPhoto
from app.models.history import History
from app.models.user import User
from app.models.sector import Sector
from app.models.category import Category


NAVY = RGBColor(20, 43, 73)
BLUE = RGBColor(0, 125, 190)
LIGHT_BLUE = RGBColor(226, 240, 248)
DARK = RGBColor(45, 55, 65)
GREY = RGBColor(110, 120, 130)
WHITE = RGBColor(255, 255, 255)
GREEN = RGBColor(35, 135, 90)
ORANGE = RGBColor(220, 135, 35)

LOCAL_TZ = ZoneInfo("Africa/Casablanca")


def _local_datetime(value):
    if not value:
        return "Non renseignée"

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(LOCAL_TZ).strftime("%d/%m/%Y à %H:%M")


def _status_label(status):
    return {
        "EN_ATTENTE": "En attente",
        "EN_COURS_DE_TRAITEMENT": "En cours de traitement",
        "TRAITEE": "Traitée",
    }.get(status, status or "Non renseigné")


def _add_text(slide, text, x, y, width, height,
              size=12, color=DARK, bold=False,
              align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(
        Inches(x), Inches(y), Inches(width), Inches(height)
    )
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = Inches(0.06)
    frame.margin_right = Inches(0.06)
    frame.margin_top = Inches(0.03)
    frame.margin_bottom = Inches(0.03)

    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    run = paragraph.add_run()
    run.text = str(text)
    run.font.name = "Aptos"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return box


def _add_header(slide, title, subtitle=None):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        0, 0, Inches(13.333), Inches(0.82)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = NAVY
    shape.line.fill.background()

    _add_text(
        slide, title, 0.45, 0.12, 12.3, 0.35,
        size=22, color=WHITE, bold=True
    )

    if subtitle:
        _add_text(
            slide, subtitle, 0.48, 0.51, 12.2, 0.2,
            size=9, color=LIGHT_BLUE
        )


def _add_photo(slide, photo, x, y, width, height, upload_folder):
    """
    Affiche uniquement une photo réellement disponible.
    Aucun cadre vide ni texte de remplacement ne sera ajouté.
    """

    if not photo or not photo.file_path:
        return

    raw_path = photo.file_path.replace("\\", "/").strip()
    relative = Path(raw_path)

    # Vérification de sécurité du chemin
    if (
        not raw_path
        or relative.is_absolute()
        or ".." in relative.parts
        or (relative.parts and ":" in relative.parts[0])
    ):
        return

    root = Path(upload_folder).resolve()
    candidate = (root / relative).resolve()

    try:
        candidate.relative_to(root)

        if not candidate.is_file():
            return

        # Afficher directement la photo, sans cadre vide
        slide.shapes.add_picture(
            str(candidate),
            Inches(x),
            Inches(y),
            width=Inches(width),
            height=Inches(height)
        )

    except (ValueError, OSError):
        return

    except Exception:
        return


def _add_field(slide, label, value, x, y, width, height=0.42):
    _add_text(
        slide, label.upper(), x, y, width, 0.17,
        size=8, color=BLUE, bold=True
    )
    _add_text(
        slide, value if value not in (None, "") else "Non renseigné",
        x, y + 0.17, width, height - 0.15,
        size=10, color=DARK
    )


def _history_dates(anomaly):
    histories = History.query.filter_by(
        anomaly_id=anomaly.id
    ).order_by(History.created_at.asc(), History.id.asc()).all()

    declaration = anomaly.created_at
    treatment_start = None
    treatment_end = anomaly.treated_at

    for event in histories:
        if event.new_status == "EN_ATTENTE" and declaration is None:
            declaration = event.created_at

        elif (
            event.new_status == "EN_COURS_DE_TRAITEMENT"
            and treatment_start is None
        ):
            treatment_start = event.created_at

        elif event.new_status == "TRAITEE" and treatment_end is None:
            treatment_end = event.created_at

    return declaration, treatment_start, treatment_end


def _add_anomaly_slide(prs, anomaly, upload_folder):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    subtitle = (
        f"{anomaly.reference} | "
        f"{_status_label(anomaly.status)}"
    )
    _add_header(slide, anomaly.title, subtitle)

    photos = AnomalyPhoto.query.filter_by(
        anomaly_id=anomaly.id
    ).order_by(
        AnomalyPhoto.uploaded_at.asc(),
        AnomalyPhoto.id.asc()
    ).all()

    before_photos = [
        p for p in photos if p.photo_type == "AVANT"
    ][:2]

    after_photos = [
        p for p in photos if p.photo_type == "APRES"
    ][:2]

    _add_text(
        slide, "PHOTOS AVANT TRAITEMENT",
        0.45, 1.0, 5.9, 0.25, size=11, color=NAVY, bold=True
    )
    _add_text(
        slide, "PHOTOS APRÈS TRAITEMENT",
        6.85, 1.0, 5.9, 0.25, size=11, color=NAVY, bold=True
    )

    photo_w = 2.85
    photo_h = 1.65

    positions = [
        (0.45, 1.32),
        (3.45, 1.32),
        (6.85, 1.32),
        (9.85, 1.32)
    ]

    # Photos AVANT : maximum 2
    for index, photo in enumerate(before_photos):
        _add_photo(
            slide,
            photo,
            *positions[index],
            photo_w,
            photo_h,
            upload_folder
        )

    # Photos APRÈS : maximum 2
    for index, photo in enumerate(after_photos):
        _add_photo(
            slide,
            photo,
            *positions[index + 2],
            photo_w,
            photo_h,
            upload_folder
        )

    technician = User.query.get(anomaly.technician_id)
    sector = Sector.query.get(anomaly.sector_id)
    category = Category.query.get(anomaly.category_id)

    declaration, treatment_start, treatment_end = _history_dates(anomaly)

    _add_text(
        slide, "INFORMATIONS DE L'ANOMALIE",
        0.45, 3.25, 12.2, 0.25, size=12, color=NAVY, bold=True
    )

    left_x = 0.5
    right_x = 6.85
    col_w = 5.9

    _add_field(
        slide, "Référence", anomaly.reference,
        left_x, 3.58, col_w
    )

    _add_field(
        slide, "Catégorie", category.name if category else None,
        right_x, 3.58, col_w
    )

    _add_field(
        slide, "Secteur", sector.name if sector else None,
        left_x, 4.12, col_w
    )

    _add_field(
        slide, "Technicien déclarant",
        technician.full_name if technician else None,
        right_x, 4.12, col_w
    )

    _add_field(
        slide, "Date et heure de déclaration",
        _local_datetime(declaration),
        left_x, 4.66, col_w
    )

    _add_field(
        slide, "Début du traitement",
        _local_datetime(treatment_start),
        right_x, 4.66, col_w
    )

    _add_field(
        slide, "Fin du traitement",
        _local_datetime(treatment_end),
        left_x, 5.20, col_w
    )

    _add_field(
        slide, "Méthode de déclaration",
        anomaly.declaration_method,
        right_x, 5.20, col_w
    )

    gps = "Non renseignées"

    if anomaly.latitude is not None and anomaly.longitude is not None:
        gps = (
            f"{float(anomaly.latitude):.7f}, "
            f"{float(anomaly.longitude):.7f}"
        )

    _add_field(
        slide, "Coordonnées GPS", gps,
        left_x, 5.74, col_w
    )

    _add_field(
        slide, "Adresse / localisation",
        anomaly.location_address,
        right_x, 5.74, col_w
    )

    _add_text(
        slide, "DESCRIPTION",
        0.5, 6.30, 12.0, 0.18,
        size=8, color=BLUE, bold=True
    )

    _add_text(
        slide, anomaly.description or "Aucune description",
        0.5, 6.49, 12.0, 0.65,
        size=9, color=DARK
    )

    _add_text(
        slide, "ZÉRO ANOMALIE",
        10.7, 7.15, 2.1, 0.18,
        size=8, color=GREY, align=PP_ALIGN.RIGHT
    )


def _add_cover(prs, start_date, end_date, total, generated_at):
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    background = slide.background
    background.fill.solid()
    background.fill.fore_color.rgb = NAVY

    _add_text(
        slide, "ZÉRO ANOMALIE",
        0.9, 1.35, 11.5, 0.75,
        size=34, color=WHITE, bold=True,
        align=PP_ALIGN.CENTER
    )

    _add_text(
        slide, "RAPPORT DE SUIVI DES ANOMALIES",
        0.9, 2.35, 11.5, 0.5,
        size=21, color=LIGHT_BLUE, bold=True,
        align=PP_ALIGN.CENTER
    )

    _add_text(
        slide,
        f"Période : du {start_date.strftime('%d/%m/%Y')} "
        f"au {end_date.strftime('%d/%m/%Y')}",
        1.2, 3.55, 10.9, 0.4,
        size=16, color=WHITE,
        align=PP_ALIGN.CENTER
    )

    _add_text(
        slide, f"Nombre total d'anomalies : {total}",
        1.2, 4.25, 10.9, 0.4,
        size=17, color=WHITE, bold=True,
        align=PP_ALIGN.CENTER
    )

    _add_text(
        slide, f"Rapport généré le {_local_datetime(generated_at)}",
        1.2, 6.35, 10.9, 0.3,
        size=10, color=LIGHT_BLUE,
        align=PP_ALIGN.CENTER
    )


def _add_summary(prs, anomalies):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, "SYNTHÈSE DES ANOMALIES")

    counts = {}

    for anomaly in anomalies:
        category = Category.query.get(anomaly.category_id)
        name = category.name if category else "Catégorie inconnue"
        counts[name] = counts.get(name, 0) + 1

    rows = sorted(counts.items(), key=lambda item: item[0].lower())

    table_shape = slide.shapes.add_table(
        len(rows) + 1,
        2,
        Inches(1.0),
        Inches(1.45),
        Inches(11.2),
        Inches(min(4.9, 0.42 * (len(rows) + 1)))
    )

    table = table_shape.table
    table.columns[0].width = Inches(8.4)
    table.columns[1].width = Inches(2.8)

    headers = ["Catégorie", "Nombre d'anomalies"]

    for col, text in enumerate(headers):
        cell = table.cell(0, col)
        cell.text = text
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE

        for paragraph in cell.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(12)
                run.font.color.rgb = WHITE

    for row_index, (name, count) in enumerate(rows, start=1):
        for col_index, value in enumerate((name, str(count))):
            cell = table.cell(row_index, col_index)
            cell.text = value
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = (
                WHITE if row_index % 2 else LIGHT_BLUE
            )

            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(11)
                    run.font.color.rgb = DARK

    _add_text(
        slide, f"TOTAL : {len(anomalies)} anomalie(s)",
        1.0, 6.55, 11.2, 0.35,
        size=16, color=NAVY, bold=True
    )


def generate_powerpoint(anomalies, start_date, end_date, upload_folder):
    prs = Presentation()

    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    generated_at = datetime.now(timezone.utc)

    _add_cover(
        prs,
        start_date,
        end_date,
        len(anomalies),
        generated_at
    )

    _add_summary(prs, anomalies)

    for anomaly in anomalies:
        _add_anomaly_slide(prs, anomaly, upload_folder)

    output = BytesIO()
    prs.save(output)
    output.seek(0)

    return output
