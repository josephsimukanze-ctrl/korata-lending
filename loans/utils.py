# loans/utils.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
from io import BytesIO
from django.http import HttpResponse
from datetime import datetime

def generate_loan_agreement_pdf(loan, agreement, payment_schedule):
    """Generate PDF loan agreement using reportlab"""
    
    # Create buffer for PDF
    buffer = BytesIO()
    
    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=20,
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=10,
        spaceBefore=15,
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    
    # Build document elements
    story = []
    
    # Header
    story.append(Paragraph("KORATA LENDING SYSTEM", title_style))
    story.append(Paragraph("LOAN AGREEMENT", styles['Heading2']))
    story.append(Paragraph(f"Agreement No: {agreement.agreement_number}", normal_style))
    story.append(Paragraph(f"Date: {agreement.agreement_date.strftime('%B %d, %Y')}", normal_style))
    story.append(Spacer(1, 20))
    
    # 1. Parties
    story.append(Paragraph("1. PARTIES TO THE AGREEMENT", heading_style))
    
    parties_data = [
        ["Lender:", "Korata Lending System\nLusaka, Zambia\ninfo@korata.com"],
        ["Borrower:", f"{loan.client.full_name}\nNRC: {loan.client.nrc}\nPhone: {loan.client.phone_number}\nEmail: {loan.client.email or 'N/A'}\nAddress: {loan.client.physical_address}\nCity: {loan.client.city}"],
    ]
    
    parties_table = Table(parties_data, colWidths=[100, 350])
    parties_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 10))
    
    # 2. Loan Details
    story.append(Paragraph("2. LOAN DETAILS", heading_style))
    
    loan_data = [
        ["Loan ID:", loan.loan_id],
        ["Principal Amount:", f"ZMW {loan.principal:,.2f}"],
        ["Interest Rate:", f"{loan.interest_rate}% per {loan.interest_period}"],
        ["Duration:", f"{loan.duration_weeks} weeks"],
        ["Total Interest:", f"ZMW {loan.total_interest:,.2f}"],
        ["Total Payback:", f"ZMW {loan.total_payback:,.2f}"],
        ["Weekly Payment:", f"ZMW {loan.weekly_payment:,.2f}"],
        ["Start Date:", loan.created_at.strftime('%B %d, %Y')],
    ]
    
    loan_table = Table(loan_data, colWidths=[120, 300])
    loan_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
    ]))
    story.append(loan_table)
    story.append(Spacer(1, 10))
    
    # 3. Collateral Information
    story.append(Paragraph("3. COLLATERAL INFORMATION", heading_style))
    
    if loan.collateral:
        collateral_data = [
            ["Asset Type:", loan.collateral.get_asset_type_display()],
            ["Asset Title:", loan.collateral.title],
            ["Serial Number:", loan.collateral.serial_number],
            ["Estimated Value:", f"ZMW {loan.collateral.estimated_value:,.2f}"],
            ["Condition:", loan.collateral.get_condition_display()],
            ["Storage Location:", loan.collateral.storage_location],
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
    story.append(Paragraph("4. TERMS AND CONDITIONS", heading_style))
    
    terms = [
        "4.1 The Borrower agrees to repay the loan amount in full according to the payment schedule provided.",
        "4.2 Payments must be made on or before the due date. Late payments will incur a penalty fee of 5% of the payment amount.",
        "4.3 The Lender reserves the right to seize the collateral in case of default of payment for more than 30 days.",
        "4.4 Early repayment is allowed without penalty. Any early repayment will reduce the total interest accrued.",
        "4.5 The Borrower must notify the Lender of any change in contact information or employment status.",
        "4.6 Payments will be processed automatically from the Borrower's designated account.",
        "4.7 The Borrower has the right to request a loan statement at any time.",
    ]
    
    for term in terms:
        story.append(Paragraph(term, normal_style))
    
    story.append(Spacer(1, 10))
    
    # 5. Payment Schedule
    story.append(Paragraph("5. PAYMENT SCHEDULE", heading_style))
    
    # Create payment schedule table
    schedule_data = [['Week', 'Due Date', 'Amount Due (ZMW)']]
    for schedule in payment_schedule[:20]:  # Show first 20 payments
        schedule_data.append([
            str(schedule.week_number),
            schedule.due_date.strftime('%b %d, %Y'),
            f"{schedule.expected_amount:,.2f}"
        ])
    
    if len(payment_schedule) > 20:
        schedule_data.append(['...', 'See full schedule online', '...'])
    
    schedule_table = Table(schedule_data, colWidths=[80, 120, 150])
    schedule_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(schedule_table)
    story.append(Spacer(1, 15))
    
    # 6. Acknowledgment
    story.append(Paragraph("6. ACKNOWLEDGMENT", heading_style))
    story.append(Paragraph("The Borrower acknowledges that they have read, understood, and agree to be bound by all the terms and conditions stated in this agreement.", normal_style))
    story.append(Spacer(1, 10))
    
    # Signatures
    story.append(Spacer(1, 30))
    
    # Signature lines
    signature_data = [
        ["", ""],
        ["_______________________", "_______________________"],
        ["Borrower's Signature", "Lender's Signature"],
        ["", ""],
        ["", ""],
        ["Date: _______________", f"Date: {datetime.now().strftime('%B %d, %Y')}"],
    ]
    
    signature_table = Table(signature_data, colWidths=[200, 200])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
    ]))
    story.append(signature_table)
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("This agreement is legally binding once signed by both parties.", ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.grey,
    )))
    story.append(Paragraph(f"Korata Lending System | {agreement.agreement_number}", ParagraphStyle(
        'PageFooter',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.grey,
    )))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF from buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf