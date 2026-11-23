import os

from django.http import FileResponse, Http404


def serve_file(fieldfile, as_attachment=False):
    """Stream a stored file through Django so access can be permission-checked."""
    if not fieldfile:
        raise Http404("No file attached.")
    try:
        handle = fieldfile.open("rb")
    except (FileNotFoundError, ValueError, OSError):
        raise Http404("File not found.")
    return FileResponse(
        handle,
        as_attachment=as_attachment,
        filename=os.path.basename(fieldfile.name),
    )
