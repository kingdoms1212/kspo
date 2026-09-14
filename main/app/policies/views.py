"""Policy listing controller: dialog fragment or standalone page."""
from ..common.partials import render_screen
from .services import policy_panel


def policies(request):
    context = {'page': 'policies', **policy_panel()}
    return render_screen(request, 'policies/index.html', 'policies/_list.html', context)
