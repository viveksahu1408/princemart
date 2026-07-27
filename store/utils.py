import os
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa

# Global Font Registration (Ek hi baar register hoga)
FONT_PATH = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'NotoSans.ttf')
if os.path.exists(FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont('NotoSans', FONT_PATH))
    except Exception as e:
        print(f'Font registration warning: {e}')


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="invoice.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('PDF generation error', status=500)
    return response