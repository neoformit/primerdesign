"""Provide user interface for requesting primer design analysis."""

import pprint
from django.shortcuts import render
from django.conf import settings
from .primer import PrimerDesign
from .forms import PrimerForm

import logging
logger = logging.getLogger('django')


def index(request):
    """Collect user input and run primer design prediction."""
    if request.method == "POST":
        form = PrimerForm(request.POST)
        if form.is_valid():
            result = PrimerDesign(form.cleaned_data)
            logger.info(
                f"Assay Design returned {len(result)} results"
                f" with {result.total_assay_count} assays:\n{result}")
            return render(request, 'design/result.html', {
                'result': result
            })
        if settings.PRIMER3_DEBUG:
            logger.info('Form was not validated')
            logger.info('Form errors:\n'
                        + pprint.pformat(form.errors, indent=4))
            logger.info(pprint.pformat(form.cleaned_data, indent=4))
        return render(request, 'design/index.html', {'form': form})

    form = PrimerForm()
    return render(request, 'design/index.html', {'form': form})
