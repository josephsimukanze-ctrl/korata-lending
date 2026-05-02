# loans/pdf_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from django.http import HttpResponse
from datetime import datetime

def generate_loan_agreement_pdf(loan, agreement, payment_schedule):
    """Generate professional loan agreement PDF"""
    
    # Create buffer
    buffer = BytesIO()
    
    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.8*inch,
        bottomMargin=0.8*inch,
        leftMargin=0.8*inch,
        rightMargin=0.8*inch,
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    
    # Section title style
    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2563eb'),
        spaceBefore=12,
        spaceAfter=8,
        leftIndent=0,
    )
    
    # Normal text style
    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
    )
    
    # Small text style
    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_CENTER,
    )
    
    # Build story
    story = []
    
    # Header
    story.append(Paragraph("KORATA LENDING SYSTEM", title_style))
    story.append(Paragraph("LOAN AGREEMENT", styles['Heading2']))
    story.append(Paragraph(f"Agreement No: {agreement.agreement_number}", normal_style))
    story.append(Paragraph(f"Date: {agreement.agreement_date.strftime('%B %d, %Y')}", normal_style))
    story.append(Spacer(1, 20))
    
    # 1. Parties
    story.append(Paragraph("1. PARTIES TO THE AGREEMENT", section_style))
    
    parties_data = [
        ["Lender:", "Korata Lending System\nLusaka, Zambia\nEmail: info@korata.com"],
        ["Borrower:", f"{loan.client.full_name}\nNRC: {loan.client.nrc}\nPhone: {loan.client.phone_number}\nEmail: {loan.client.email or 'N/A'}\nAddress: {loan.client.physical_address}\nCity: {loan.client.city}"],
    ]
    
    parties_table = Table(parties_data, colWidths=[100, 340])
    parties_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 10))
    
    # 2. Loan Details
    story.append(Paragraph("2. LOAN DETAILS", section_style))
    
    loan_data = [
        ["Loan ID:", loan.loan_id],
        ["Principal Amount:", f"ZMW {loan.principal:,.2f}"],
        ["Interest Rate:", f"{loan.interest_rate}% per {loan.interest_period}"],
        ["Duration:", f"{loan.duration_weeks} weeks"],
        ["Total Interest:", f"ZMW {loan.total_interest:,.2f}"],
        ["Total Payback:", f"<b>ZMW {loan.total_payback:,.2f}</b>"],
        ["Weekly Payment:", f"<b>ZMW {loan.weekly_payment:,.2f}</b>"],
        ["Start Date:", loan.created_at.strftime('%B %d, %Y')],
    ]
    
    loan_table = Table(loan_data, colWidths=[120, 300])
    loan_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
    ]))
    story.append(loan_table)
    story.append(Spacer(1, 10))
    
    # 3. Collateral
    story.append(Paragraph("3. COLLATERAL INFORMATION", section_style))
    
    if loan.collateral:
        collateral_data = [
            ["Asset Type:", loan.collateral.get_asset_type_display()],
            ["Description:", loan.collateral.title],
            ["Serial Number:", loan.collateral.serial_number],
            ["Estimated Value:", f"ZMW {loan.collateral.estimated_value:,.2f}"],
            ["Condition:", loan.collateral.get_condition_display()],
            ["Location:", loan.collateral.storage_location],
        ]
        
        collateral_table = Table(collateral_data, colWidths=[120, 300])
        collateral_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(collateral_table)
    else:
        story.append(Paragraph("No collateral provided for this loan.", normal_style))
    
    story.append(Spacer(1, 10))
    
    # 4. Terms and Conditions
    story.append(Paragraph("4. TERMS AND CONDITIONS", section_style))
    
    terms = [
        "4.1 The Borrower agrees to repay the loan amount in full according to the payment schedule.",
        "4.2 Late payments will incur a penalty fee of 5% of the payment amount.",
        "4.3 The Lender may seize the collateral in case of default for more than 30 days.",
        "4.4 Early repayment is allowed without penalty.",
        "4.5 The Borrower must notify the Lender of any change in contact information.",
        "4.6 This agreement is legally binding once signed by both parties.",
    ]
    
    for term in terms:
        story.append(Paragraph(term, normal_style))
    
    story.append(Spacer(1, 10))
    
    # 5. Payment Schedule (first 10 payments)
    story.append(Paragraph("5. PAYMENT SCHEDULE (First 10 Payments)", section_style))
    
    schedule_data = [['Week', 'Due Date', 'Amount (ZMW)']]
    count = 0
    for schedule in payment_schedule:
        if count >= 10:
            schedule_data.append(['...', 'See full schedule in your dashboard', '...'])
            break
        schedule_data.append([
            str(schedule.week_number),
            schedule.due_date.strftime('%d %b %Y'),
            f"{schedule.expected_amount:,.2f}"
        ])
        count += 1
    
    schedule_table = Table(schedule_data, colWidths=[80, 120, 120])
    schedule_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -2), 1, colors.lightgrey),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(schedule_table)
    story.append(Spacer(1, 15))
    
    # 6. Signatures
    story.append(Paragraph("6. SIGNATURES", section_style))
    story.append(Spacer(1, 30))
    
    # Signature lines
    signature_data = [
        ["", ""],
        ["_________________________", "_________________________"],
        ["Borrower's Signature", "Lender's Signature"],
        ["", ""],
        ["Date: _______________", f"Date: {datetime.now().strftime('%B %d, %Y')}"],
    ]
    
    signature_table = Table(signature_data, colWidths=[200, 200])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
    ]))
    story.append(signature_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("This agreement is legally binding once signed by both parties.", small_style))
    story.append(Paragraph(f"Korata Lending System | {agreement.agreement_number}", small_style))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF value
    pdf_value = buffer.getvalue()
    buffer.close()
    
    return pdf_value