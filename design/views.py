"""Provide user interface for requesting primer design analysis."""

import os
import pprint
import pickle
from django.shortcuts import render
from django.conf import settings
from .primer import PrimerDesign
from .forms import PrimerForm

import logging
logger = logging.getLogger('django')


def index(request):
    """Collect user input and run primer design prediction."""
    if request.method == "POST":
        # !!!
        TEST = False

        pkl = os.path.join(settings.BASE_DIR, 'design', 'result.pkl')
        if os.path.exists(pkl) and TEST:
            with open(pkl, 'rb') as p:
                result = pickle.load(p)
            return render(request, 'design/result.html', {
                'queries': result.iterations
            })

        # # TODO: Remove above

        form = PrimerForm(request.POST)
        if form.is_valid():
            result = PrimerDesign(form.cleaned_data)

            with open(pkl, 'wb') as p:
                pickle.dump(result, p)
            # # TODO: Remove above

            return render(request, 'design/result.html', {
                'queries': result.iterations
            })
        logger.info('Form was not validated')
        logger.info('Form errors:\n' + pprint.pformat(form.errors, indent=4))
        logger.info(pprint.pformat(form.cleaned_data, indent=4))
        return render(request, 'design/index.html', {'form': form})

    form = PrimerForm()
    return render(request, 'design/index.html', {'form': form})
