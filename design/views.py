"""Provide user interface for requesting primer design analysis."""

from django.shortcuts import render
# from django.core.exceptions import SuspiciousOperation
from .primer import PrimerDesign
from .forms import PrimerForm


def index(request):
    """Collect user input and run primer design prediction."""
    if request.method == "POST":
        form = PrimerForm(request.POST)
        if form.is_valid():
            result = PrimerDesign(form.cleaned_data)
            return render(request, 'design/result.html', result.to_dict())
        return render(request, 'design/index.html', {'form': form})

    form = PrimerForm()
    return render(request, 'design/index.html', {'form': form})
