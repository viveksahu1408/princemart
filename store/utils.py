import os
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import get_template
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa
import json
from .models import DeliveryZone


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

def is_point_in_polygon(point, polygon):
    """Ray-casting algorithm to check if a lat/lng point is inside a polygon boundary."""
    x, y = point
    inside = False
    n = len(polygon)

    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def is_location_deliverable(user_lat, user_lng):
    """Check if the given lat/lng falls into any active DeliveryZone."""
    active_zones = DeliveryZone.objects.filter(is_active=True)

    for zone in active_zones:
        coordinates = zone.get_coordinates_list()
        if not coordinates or len(coordinates) < 3:
            continue

        # Check if coordinates are [lat, lng] or [lng, lat]
        formatted_polygon = []
        for pt in coordinates:
            if isinstance(pt, dict):
                formatted_polygon.append((float(pt.get('lat')), float(pt.get('lng'))))
            elif isinstance(pt, (list, tuple)):
                formatted_polygon.append((float(pt[0]), float(pt[1])))

        if is_point_in_polygon((user_lat, user_lng), formatted_polygon):
            return True

    return False