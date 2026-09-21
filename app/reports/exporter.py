import os
import tempfile
import csv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

class ReportExporter:
    @staticmethod
    def export_csv(filepath, beam, solution, forces, equations, critical):
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Reactions
            writer.writerow(['REACCIONES'])
            writer.writerow(['Apoyo', 'x (m)', 'Horizontal (kN)', 'Vertical (kN)', 'Momento (kN·m)'])
            support_dict = {s.name: s.position for s in beam.supports}
            for support_name, reactions in solution.reactions.items():
                pos_x = support_dict.get(support_name, 0.0)
                writer.writerow([
                    support_name, 
                    f"{pos_x:.3f}",
                    f"{reactions.get('Rx', 0.0):.3f}", 
                    f"{reactions.get('Ry', 0.0):.3f}", 
                    f"{reactions.get('M', 0.0):.3f}"
                ])
            writer.writerow([])
            
            # Critical Zones
            writer.writerow(['ZONAS CRITICAS'])
            writer.writerow(['Posicion x (m)', 'Tipo', 'Valor', 'Descripcion'])
            for z in critical.zones:
                writer.writerow([f"{z.x_position:.3f}", z.zone_type, f"{z.value:.2f}", z.description])
            writer.writerow([])
            
            # Equations
            writer.writerow(['ECUACIONES POR TRAMO'])
            writer.writerow(['Inicio tramo x (m)', 'Fin tramo x (m)', 'Fuerza Cortante V(x)', 'Momento Flector M(x)'])
            for inter in equations.intervals:
                writer.writerow([
                    f"{inter.x_start:.2f}", 
                    f"{inter.x_end:.2f}", 
                    str(inter.V_expr), 
                    str(inter.M_expr)
                ])

    @staticmethod
    def export_pdf(filepath, beam, solution, forces, equations, critical, shear_fig, moment_fig):
        doc = SimpleDocTemplate(filepath, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=1, textColor=colors.HexColor('#0969da'))
        h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], textColor=colors.HexColor('#24292f'), spaceBefore=15, spaceAfter=5)
        normal_style = styles['Normal']
        
        elements = []
        
        # Title
        elements.append(Paragraph("Reporte de Análisis Estructural - BeamAnalyzer Pro", title_style))
        elements.append(Spacer(1, 20))
        
        # 1. Datos de la viga
        elements.append(Paragraph("1. Información del Modelo", h2_style))
        elements.append(Paragraph(f"<b>Longitud total:</b> {beam.length:.2f} m", normal_style))
        elements.append(Paragraph(f"<b>Apoyos:</b> {len(beam.supports)}", normal_style))
        elements.append(Paragraph(f"<b>Cargas aplicadas:</b> {len(beam.loads)}", normal_style))
        elements.append(Spacer(1, 10))
        
        # 2. Reacciones
        elements.append(Paragraph("2. Reacciones en Apoyos", h2_style))
        data = [['Apoyo', 'x (m)', 'Horizontal (kN)', 'Vertical (kN)', 'Momento (kN·m)']]
        support_dict = {s.name: s.position for s in beam.supports}
        for support_name, reactions in solution.reactions.items():
            pos_x = support_dict.get(support_name, 0.0)
            data.append([
                support_name,
                f"{pos_x:.3f}",
                f"{reactions.get('Rx', 0.0):.3f}",
                f"{reactions.get('Ry', 0.0):.3f}",
                f"{reactions.get('M', 0.0):.3f}"
            ])
        
        t = Table(data, colWidths=[80, 80, 80, 80, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f6f8fa')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#24292f')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d0d7de'))
        ]))
        elements.append(t)
        elements.append(Spacer(1, 15))
        
        # Save figures to temp files
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f_shear:
            shear_fig.savefig(f_shear.name, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            shear_path = f_shear.name
            
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f_moment:
            moment_fig.savefig(f_moment.name, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            moment_path = f_moment.name
            
        # 3. Diagramas
        elements.append(Paragraph("3. Diagramas de Esfuerzos Internos", h2_style))
        elements.append(Image(shear_path, width=450, height=180))
        elements.append(Spacer(1, 10))
        elements.append(Image(moment_path, width=450, height=180))
        elements.append(Spacer(1, 15))
        
        # 4. Critical Zones
        elements.append(Paragraph("4. Valores Máximos e Interpretación", h2_style))
        c_data = [['Posición x (m)', 'Tipo', 'Valor', 'Descripción']]
        for z in critical.zones:
            c_data.append([
                f"{z.x_position:.3f}", 
                Paragraph(z.zone_type, normal_style), 
                f"{z.value:.2f}", 
                Paragraph(z.description, normal_style)
            ])
            
        tc = Table(c_data, colWidths=[80, 100, 60, 250])
        tc.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f6f8fa')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#24292f')),
            ('ALIGN', (0,0), (2,-1), 'CENTER'),
            ('ALIGN', (3,1), (3,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d0d7de'))
        ]))
        elements.append(tc)
        elements.append(Spacer(1, 10))
        
        # Interpretacion
        for msg in critical.messages:
            elements.append(Paragraph(f"• {msg}", normal_style))
            
        m_max = critical.max_values.get("M_abs_max", 0.0)
        if m_max > 0:
            elements.append(Spacer(1, 5))
            elements.append(Paragraph(f"<i>El diseño a flexión estará gobernado por un momento de {m_max:.2f} kN·m.</i>", normal_style))
            
        elements.append(Spacer(1, 15))
        
        # 5. Equations
        elements.append(Paragraph("5. Ecuaciones por Tramo", h2_style))
        for inter in equations.intervals:
            elements.append(Paragraph(f"<b>TRAMO desde x = {inter.x_start:.2f} m hasta x = {inter.x_end:.2f} m</b>", normal_style))
            eq_v = str(inter.V_expr).replace('**', '^').replace('*', '')
            eq_m = str(inter.M_expr).replace('**', '^').replace('*', '')
            elements.append(Paragraph(f"&nbsp;&nbsp;Fuerza Cortante: V(x) = {eq_v}", normal_style))
            elements.append(Paragraph(f"&nbsp;&nbsp;Momento Flector: M(x) = {eq_m}", normal_style))
            elements.append(Spacer(1, 5))
            
        doc.build(elements)
        
        # Cleanup
        try:
            os.remove(shear_path)
            os.remove(moment_path)
        except:
            pass
