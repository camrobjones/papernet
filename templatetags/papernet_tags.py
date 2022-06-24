"""
Papernet Django Template Tags
-----------------------------
"""

from django import template
from django.utils import timezone as tz

register = template.Library()


@register.filter
def nice_date(dt):
    """Return a friendly string describing the datetime"""
    if dt is None:
        return "Never"

    delta = tz.now() - dt
    secs = delta.total_seconds()

    if secs <= 30:
        return "A few seconds ago"

    if secs <= 3600:
        mins = round(secs/60)
        s = "s" if mins != 1 else ""
        return f"{mins} minute{s} ago"

    if secs <= 86400:
        hours = round(secs / 3600)
        s = "s" if hours != 1 else ""
        return f"{hours} hour{s} ago"

    if delta.days < 2:
        time = dt.strftime("%-I %p")
        return f"{time} Yesterday"

    if delta.days < 7:
        return f"{delta.days} days ago"

    if delta.days < 30:
        weeks = round(delta.days / 7)
        s = "s" if weeks != 1 else ""
        return f"{weeks} week{s} ago"

    if delta.days < 60:
        return f"Last month"

    if delta.days < 365:
        return dt.strftime("%a %b")

    return dt.strftime("%a %b %Y")
