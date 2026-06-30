# export_pdf.py  ?  Reporte de Examen de Conduccion


import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
from reportlab.graphics import renderPDF
from reportlab.graphics.charts.piecharts import Pie


C_DARK    = colors.HexColor("#0D1117")
C_PANEL   = colors.HexColor("#161B22")
C_BORDER  = colors.HexColor("#30363D")
C_GREEN   = colors.HexColor("#3FB950")
C_RED     = colors.HexColor("#F85149")
C_YELLOW  = colors.HexColor("#D29922")
C_BLUE    = colors.HexColor("#58A6FF")
C_TEXT    = colors.HexColor("#E6EDF3")
C_SUBTEXT = colors.HexColor("#8B949E")
C_WHITE   = colors.white
C_GOLD    = colors.HexColor("#FFD700")



def _generar_consejos(grade, cones_hit, cp_done, cp_names):
    """Genera consejos personalizados segun el resultado del examen."""
    consejos = []

    # Evaluacion global
    if grade >= 90:
        consejos.append({
            "titulo": "Excelente desempeno",
            "texto": (
                "Demostraste un dominio sobresaliente del vehiculo. Mantuviste el "
                "control en todas las zonas y completaste el recorrido con minimas "
                "penalizaciones. Continua practicando para conservar este nivel."
            ),
            "color": C_GREEN,
            "icono": "*"
        })
    elif grade >= 70:
        consejos.append({
            "titulo": "Buen desempeno general",
            "texto": (
                "Completaste el examen satisfactoriamente. Hay areas de mejora "
                "puntuales, pero tu manejo del vehiculo fue correcto en la mayoria "
                "de las situaciones evaluadas."
            ),
            "color": C_BLUE,
            "icono": "+"
        })
    elif grade >= 50:
        consejos.append({
            "titulo": "Desempeno aceptable con areas de mejora",
            "texto": (
                "Aprobaste el examen, pero se identificaron varias areas que "
                "requieren practica adicional. Revisa cada seccion detalladamente "
                "y considera repetir el simulador enfocandote en los puntos debiles."
            ),
            "color": C_YELLOW,
            "icono": "?"
        })
    else:
        consejos.append({
            "titulo": "Se requiere practica adicional",
            "texto": (
                "El resultado indica que necesitas reforzar las habilidades de "
                "conduccion antes de un examen real. No te desanimes: usa el "
                "simulador repetidamente enfocandote en cada zona por separado."
            ),
            "color": C_RED,
            "icono": "x"
        })

    # Conos
    if cones_hit == 0:
        consejos.append({
            "titulo": "Control perfecto de espacios",
            "texto": (
                "No golpeaste ningun cono durante todo el recorrido. Esto refleja "
                "una excelente percepcion del espacio del vehiculo y un buen "
                "control de la trayectoria."
            ),
            "color": C_GREEN,
            "icono": "o"
        })
    elif cones_hit <= 2:
        consejos.append({
            "titulo": "Atencion a la proximidad de obstaculos",
            "texto": (
                f"Golpeaste {cones_hit} cono(s). En situaciones reales esto "
                "podria representar un riesgo. Practica reducir la velocidad al "
                "aproximarte a zonas con obstaculos y amplia tu vision periferica."
            ),
            "color": C_YELLOW,
            "icono": "o"
        })
    else:
        consejos.append({
            "titulo": "Mejorar percepcion espacial del vehiculo",
            "texto": (
                f"Golpeaste {cones_hit} conos durante el examen. Te recomendamos "
                "practicar maniobras de precision a baja velocidad: estacionamiento, "
                "zigzag lento y aproximaciones controladas a obstaculos."
            ),
            "color": C_RED,
            "icono": "o"
        })

    # Checkpoints individuales
    for i, (done, name) in enumerate(zip(cp_done, cp_names)):
        if not done:
            consejos.append({
                "titulo": f"Zona incompleta: {name}",
                "texto": (
                    f"No completaste la zona '{name}'. Revisa los requisitos "
                    "de esa prueba y practica el tipo de maniobra que exige "
                    "antes de realizar el examen nuevamente."
                ),
                "color": C_RED,
                "icono": ">"
            })

    # Consejo de estacionamiento si aplica
    if any("ESTACION" in n.upper() for n, d in zip(cp_names, cp_done) if d):
        consejos.append({
            "titulo": "Tecnica de estacionamiento",
            "texto": (
                "El estacionamiento requiere paciencia y vision de la trayectoria "
                "completa. Practica identificar la posicion de referencia antes de "
                "iniciar la maniobra y usa velocidades muy bajas para ajustar."
            ),
            "color": C_BLUE,
            "icono": "P"
        })

    # Consejo general de velocidad
    consejos.append({
        "titulo": "Recomendacion general",
        "texto": (
            "En el examen de conduccion real, mantener la velocidad adecuada "
            "segun la zona es fundamental. Usa la transmision manual correctamente: "
            "marcha baja para zonas de habilidad, marcha alta para rectas. "
            "La anticipacion y suavidad en los controles son la clave del exito."
        ),
        "color": C_SUBTEXT,
        "icono": "i"
    })

    return consejos


# ?? Barra de progreso dibujada con reportlab ???????????????????????????????
def _barra_progreso(valor, maximo, ancho, alto, color_fill):
    """Retorna un Drawing con una barra de progreso."""
    d = Drawing(ancho, alto + 6)
    # Fondo
    d.add(Rect(0, 3, ancho, alto, fillColor=C_BORDER, strokeColor=None))
    # Relleno
    fill_w = max(0, int(ancho * min(valor / max(maximo, 1), 1.0)))
    if fill_w > 0:
        d.add(Rect(0, 3, fill_w, alto, fillColor=color_fill, strokeColor=None))
    # Etiqueta
    pct = int(valor / max(maximo, 1) * 100)
    d.add(String(ancho + 6, 3, f"{pct}%",
                 fontName="Helvetica-Bold", fontSize=8,
                 fillColor=C_SUBTEXT))
    return d



def _gauge_nota(grade, size=120):
    """Gauge circular que muestra la nota."""
    d   = Drawing(size, size)
    cx  = size / 2; cy = size / 2; r = size / 2 - 8

    # Color segun nota
    if grade >= 70:   col = C_GREEN
    elif grade >= 50: col = C_YELLOW
    else:             col = C_RED

    # Circulo fondo
    d.add(Circle(cx, cy, r, fillColor=C_PANEL, strokeColor=C_BORDER, strokeWidth=2))
    # Circulo de progreso (simulado con arco grueso usando multiples lineas)
    # Nota como texto grande centrado
    d.add(String(cx, cy + 10, str(grade),
                 fontName="Helvetica-Bold", fontSize=32,
                 fillColor=col, textAnchor="middle"))
    d.add(String(cx, cy - 8, "/ 100",
                 fontName="Helvetica", fontSize=11,
                 fillColor=C_SUBTEXT, textAnchor="middle"))
    d.add(String(cx, cy - 24, "PUNTOS",
                 fontName="Helvetica-Bold", fontSize=8,
                 fillColor=C_SUBTEXT, textAnchor="middle"))
    return d



def exportar_resultado(resultado):
    """
    Genera el PDF de resultado y lo guarda en el escritorio o carpeta actual.
    Retorna la ruta del archivo generado.
    """
    # Datos
    grade         = resultado.get('grade', 0)
    total_penalty = resultado.get('total_penalty', 0)
    cones_hit     = resultado.get('cones_hit', 0)
    cp_done       = resultado.get('cp_done', [])
    cp_names      = resultado.get('cp_names', [])
    result        = resultado.get('result', 'DESAPROBADO')
    fecha         = resultado.get('fecha', datetime.datetime.now().strftime("%d/%m/%Y  %H:%M"))

    aprobado = grade >= 50
    color_resultado = C_GREEN if aprobado else C_RED

    # Ruta de salida — escritorio si existe, sino carpeta actual
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(desktop):
        desktop = os.path.join(os.path.expanduser("~"), "Escritorio")
    if not os.path.isdir(desktop):
        desktop = os.path.abspath(".")

    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(desktop, f"Resultado_Examen_{ts}.pdf")

    # Documento
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title="Resultado Examen de Conduccion",
        author="Simulador Touring Pachacamac"
    )

    W_PAGE = A4[0] - 4*cm   # ancho util

    styles = getSampleStyleSheet()

    def style(name, **kw):
        s = ParagraphStyle(name, **kw)
        return s

    S_TITLE = style("titulo",
        fontName="Helvetica-Bold", fontSize=22,
        textColor=C_TEXT, alignment=TA_CENTER, spaceAfter=4)

    S_SUBTITLE = style("subtitulo",
        fontName="Helvetica", fontSize=11,
        textColor=C_SUBTEXT, alignment=TA_CENTER, spaceAfter=2)

    S_SECTION = style("seccion",
        fontName="Helvetica-Bold", fontSize=13,
        textColor=C_BLUE, spaceBefore=14, spaceAfter=6)

    S_BODY = style("cuerpo",
        fontName="Helvetica", fontSize=10,
        textColor=C_TEXT, leading=15, spaceAfter=4)

    S_CONSEJO_TITULO = style("cons_titulo",
        fontName="Helvetica-Bold", fontSize=10,
        textColor=C_TEXT, spaceAfter=2)

    S_CONSEJO_TEXTO = style("cons_texto",
        fontName="Helvetica", fontSize=9,
        textColor=C_SUBTEXT, leading=13, spaceAfter=0)

    S_SMALL = style("pequeno",
        fontName="Helvetica", fontSize=8,
        textColor=C_SUBTEXT, alignment=TA_CENTER)

    S_RESULT = style("resultado",
        fontName="Helvetica-Bold", fontSize=28,
        textColor=color_resultado, alignment=TA_CENTER, spaceAfter=4)

    story = []

   
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("SIMULADOR TOURING PACHACAMAC", S_TITLE))
    story.append(Paragraph("Reporte Oficial de Examen de Conduccion", S_SUBTITLE))
    story.append(Paragraph(f"Fecha: {fecha}", S_SMALL))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=C_BLUE, spaceAfter=10))

   
    gauge  = _gauge_nota(grade, size=130)
    res_txt = [
        [Paragraph(result, S_RESULT)],
        [Spacer(1, 4)],
        [Paragraph(f"Calificacion: <b>{grade} / 100 puntos</b>",
                   style("rdet", fontName="Helvetica", fontSize=13,
                         textColor=C_TEXT, alignment=TA_CENTER))],
        [Paragraph(f"Conos golpeados: {cones_hit}",
                   style("rdet2", fontName="Helvetica", fontSize=11,
                         textColor=C_SUBTEXT, alignment=TA_CENTER))],
        [Paragraph(f"Puntos de penalizacion: {total_penalty}",
                   style("rdet3", fontName="Helvetica", fontSize=11,
                         textColor=C_SUBTEXT, alignment=TA_CENTER))],
        [Paragraph(
            "APROBADO ? Puede continuar al examen real" if aprobado else
            "DESAPROBADO ? Se recomienda practica adicional",
            style("reval", fontName="Helvetica-Bold", fontSize=9,
                  textColor=color_resultado, alignment=TA_CENTER)
        )],
    ]

    # Combinar gauge y texto en tabla
    header_table = Table(
        [[gauge, res_txt]],
        colWidths=[4.5*cm, W_PAGE - 4.5*cm]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN',        (0,0), (-1,-1), 'CENTER'),
        ('BACKGROUND',   (0,0), (-1,-1), C_PANEL),
        ('ROUNDEDCORNERS', [8]),
        ('BOX',          (0,0), (-1,-1), 1.5, C_BORDER),
        ('TOPPADDING',   (0,0), (-1,-1), 14),
        ('BOTTOMPADDING',(0,0), (-1,-1), 14),
        ('LEFTPADDING',  (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))

    
    story.append(Paragraph("Detalle por Zonas de Evaluacion", S_SECTION))

    cp_data = [["#", "Zona / Prueba", "Estado", "Observacion"]]
    for i, (name, done) in enumerate(zip(cp_names, cp_done), 1):
        estado  = "COMPLETADO" if done else "INCOMPLETO"
        obs     = "Maniobra ejecutada correctamente" if done \
                  else "Requiere practica adicional"
        col_est = "#3FB950" if done else "#F85149"
        cp_data.append([
            str(i),
            name,
            Paragraph(f'<font color="{col_est}"><b>{estado}</b></font>',
                      style(f"cp{i}", fontName="Helvetica-Bold", fontSize=9,
                            textColor=C_TEXT)),
            obs
        ])

    cp_table = Table(
        cp_data,
        colWidths=[0.8*cm, 6.5*cm, 3.2*cm, W_PAGE - 0.8*cm - 6.5*cm - 3.2*cm]
    )
    cp_table.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND',    (0,0), (-1,0),  C_BLUE),
        ('TEXTCOLOR',     (0,0), (-1,0),  C_WHITE),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,0),  9),
        ('ALIGN',         (0,0), (-1,0),  'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,0),  8),
        ('TOPPADDING',    (0,0), (-1,0),  8),
        # Filas de datos
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,1), (-1,-1), 9),
        ('TEXTCOLOR',     (0,1), (-1,-1), C_TEXT),
        ('ALIGN',         (0,1), (0,-1),  'CENTER'),
        ('ALIGN',         (2,1), (2,-1),  'CENTER'),
        ('BACKGROUND',    (0,1), (-1,-1), C_PANEL),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [C_PANEL, colors.HexColor("#1C2128")]),
        ('TOPPADDING',    (0,1), (-1,-1), 7),
        ('BOTTOMPADDING', (0,1), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        # Bordes
        ('GRID',          (0,0), (-1,-1), 0.5, C_BORDER),
        ('BOX',           (0,0), (-1,-1), 1.5, C_BORDER),
    ]))
    story.append(cp_table)
    story.append(Spacer(1, 0.5*cm))

   
    story.append(Paragraph("Metricas de Rendimiento", S_SECTION))

    metricas = [
        ("Calificacion final",   grade,         100, C_GREEN if grade>=70 else C_YELLOW if grade>=50 else C_RED),
        ("Control de obstaculos (sin conos)", max(0, 100 - cones_hit*10), 100, C_GREEN if cones_hit==0 else C_YELLOW if cones_hit<=2 else C_RED),
        ("Zonas completadas",    sum(cp_done),  max(len(cp_done),1), C_BLUE),
        ("Puntos conservados",   max(0, 100-total_penalty), 100, C_GREEN if total_penalty<=10 else C_YELLOW if total_penalty<=30 else C_RED),
    ]

    bar_w = W_PAGE - 5.5*cm
    met_data = []
    for label, val, maximo, col in metricas:
        display = f"{val}" if maximo == 100 else f"{val}/{maximo}"
        met_data.append([
            Paragraph(label, style("mlbl", fontName="Helvetica", fontSize=9,
                                   textColor=C_TEXT)),
            _barra_progreso(val, maximo, bar_w, 10, col),
            Paragraph(display, style("mval", fontName="Helvetica-Bold", fontSize=9,
                                     textColor=col, alignment=TA_RIGHT))
        ])

    met_table = Table(met_data, colWidths=[4.5*cm, bar_w + 0.3*cm, 1.2*cm])
    met_table.setStyle(TableStyle([
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND',    (0,0), (-1,-1), C_PANEL),
        ('TOPPADDING',    (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('BOX',           (0,0), (-1,-1), 1.5, C_BORDER),
        ('LINEBELOW',     (0,0), (-1,-2), 0.5, C_BORDER),
    ]))
    story.append(met_table)
    story.append(Spacer(1, 0.5*cm))

    
    story.append(Paragraph("Analisis y Recomendaciones", S_SECTION))

    consejos = _generar_consejos(grade, cones_hit, cp_done, cp_names)
    for c in consejos:
        icono_style = style(
            f"ic_{c['titulo'][:8]}",
            fontName="Helvetica-Bold", fontSize=14,
            textColor=c['color'], alignment=TA_CENTER
        )
        bloque = Table(
            [[Paragraph(c['icono'], icono_style),
              [Paragraph(c['titulo'], S_CONSEJO_TITULO),
               Paragraph(c['texto'], S_CONSEJO_TEXTO)]]],
            colWidths=[1.0*cm, W_PAGE - 1.0*cm]
        )
        bloque.setStyle(TableStyle([
            ('VALIGN',        (0,0), (-1,-1), 'TOP'),
            ('BACKGROUND',    (0,0), (-1,-1), C_PANEL),
            ('TOPPADDING',    (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING',   (0,0), (0,-1),  8),
            ('LEFTPADDING',   (1,0), (1,-1),  6),
            ('RIGHTPADDING',  (0,0), (-1,-1), 10),
            ('LINEAFTER',     (0,0), (0,-1),  2, c['color']),
            ('BOX',           (0,0), (-1,-1), 0.5, C_BORDER),
        ]))
        story.append(KeepTogether([bloque, Spacer(1, 0.25*cm)]))

   
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=C_BORDER, spaceAfter=6))
    story.append(Paragraph(
        "Simulador Touring Pachacamac  |  Reporte generado automaticamente  |  "
        "Para uso educativo y de evaluacion",
        S_SMALL
    ))

    # Construir PDF
    doc.build(story)
    print(f"  PDF exportado: {path}")
    return path
