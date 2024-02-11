from django.conf import settings
from pathlib import Path
import re
from django.urls import reverse
import markdown

def mimetype_to_icon(mimetype):
    type2icon = {
        'image': 'file-picture',
        'audio': 'file-music',
        'video': 'file-video',
        'application/pdf': 'file-pdf',
        'application/msword': 'file-word',
        'application/vnd.ms-word': 'file-word',
        'application/vnd.oasis.opendocument.text': 'libreoffice',
        'application/vnd.openxmlformats-officedocument.wordprocessingml': 'file-word',
        'application/vnd.ms-excel': 'file-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml': 'file-excel',
        'application/vnd.oasis.opendocument.spreadsheet': 'file-excel',
        'application/vnd.ms-powerpoint': 'file-powerpoint-o',
        'application/vnd.openxmlformats-officedocument.presentationml': 'file-powerpoint-o',
        'application/vnd.oasis.opendocument.presentation': 'file-powerpoint-o',
        'text/plain': 'file-text2',
        'text/html': 'document-file-html',
        'application/json': 'file-text2',
        'application/gzip': 'file-zip',
        'application/x-zip-compressed': 'file-zip',
        'application/zip': 'file-zip',
        'application/x-gtar': 'file-zip',
        'application/x-tar': 'file-zip',
        'application/gnutar': 'file-zip',
        'application/x-compressed': 'file-zip',
        'application/x-gzip': 'file-zip',
        'multipart/x-gzip': 'file-zip',
        'application/x-bzip': 'file-zip',
        'application/x-bzip2': 'file-zip',
        'application/x-7z-compressed': 'file-zip',
        'application/rar': 'file-zip',
    }
    
    for mime_type, icon_name in type2icon.items():
        if mime_type in mimetype:
            return "icon-" + icon_name
    return 'icon-file-empty'


def markdown_public_ressource(md):
    path_to_ressources = reverse('joplin:joplin_public_ressource', kwargs={
                                 'ressource_path': 'dontcare'})  # => /joplin_ressources/public/dontcare
    path_to_ressources = path_to_ressources[:-len("dontcare")]

    md = md.replace("](:/", "](" + path_to_ressources)
    md = md.replace('src=":/', 'src="' + path_to_ressources)

    return md

   
def markdown_joplin_to_vieweb(md, public):
    """
    Adapt the given md from joplin api so that joplin-vieweb access the images and attachments.
    Roughly: transform ![image.png](:/id) to ![image.png](/joplin/joplin_ressources/id)
    """
    return md
    # change links to image so they contain the name with the extension (html format)
    found = re.findall('<img src=":/([^"]+)" +alt="([^"]+)"', md)
    for name, ext in found:
        file_extension = Path(ext).suffix
        md = md.replace(name, name + file_extension)

    # add the path to the joplin ressources in the img and attachments:
    path_to_ressources = reverse('joplin:joplin_ressource', kwargs={
                                 'ressource_path': 'dontcare'})  # => /joplin/joplin_ressources/dontcare
    path_to_ressources = path_to_ressources[:-len("dontcare")]
    if public:
        path_to_ressources = path_to_ressources + "public/"

    md = md.replace("](:/", "](" + path_to_ressources)
    md = md.replace('src=":/', 'src="' + path_to_ressources)

    return md


def markdown_vieweb_to_joplin(md):
    """
    The opposite
    """
    path_to_ressources = reverse('joplin:joplin_ressource', kwargs={
                                 'ressource_path': 'dontcare'})  # => /joplin/joplin_ressources/dontcare
    path_to_ressources = path_to_ressources[:-len("dontcare")]
    md = md.replace('src="' + path_to_ressources, 'src=":/')
    md = md.replace("](" + path_to_ressources, "](:/")

    return md


def placeholder_backslash_doller(md: str) -> str:
    """Replace every \$ in given md by @@ANTISLASH_DOLLAR_PALCEHOLDER@@.
    Pay attention to odd \ number: \\$ is not replaced
      (nor \\\\$, but \\\$ is replaced by \\@@ANTISLASH_DOLLAR_PALCEHOLDER@@)

    Args:
        md (str): markdown to "escape"

    Returns:
        str: "escaped" markdown
    """
    index = 0
    antislash_count = 0
    antislash_dollar_indexes = []
    for letter in md:
        if letter == "$" and antislash_count % 2 == 1:
            antislash_dollar_indexes.append(index)
            antislash_count = 0
        elif letter == "\\":
            antislash_count = antislash_count + 1
        else:
            antislash_count = 0
        index = index + 1

    escape = ""
    if not antislash_dollar_indexes:
        escape = md
    else:
        last_index = 0
        for one_index in antislash_dollar_indexes:
            escape = escape + md[last_index:one_index - 1]
            escape = escape + "@@ANTISLASH_DOLLAR_PALCEHOLDER@@"
            last_index = one_index + 1
        escape = escape + md[last_index:]
    return escape


def md_to_html(md, for_preview):
    html = markdown.markdown(placeholder_backslash_doller(md), extensions=[
        'fenced_code', 'codehilite', 'toc', 'markdown.extensions.tables', 'pymdownx.mark', 'pymdownx.tabbed'])
    
    # Transform [ ] and [x] to checkboxes.
    if for_preview:
        html = html.replace("<li>[ ] ", '<li><input type="checkbox" onclick="return false;">')
        html = html.replace("<li>\n<p>[ ] ", '<li><p><input type="checkbox" onclick="return false;">')
        html = html.replace("<li>[x] ", '<li><input type="checkbox" checked onclick="return false;">')
        html = html.replace("<li>\n<p>[x] ", '<li><p><input type="checkbox" checked onclick="return false;">')
    else:
        html = html.replace("<li>[ ] ", '<li><input type="checkbox">')
        html = html.replace("<li>\n<p>[ ] ", '<li><p><input type="checkbox">')
        html = html.replace("<li>[x] ", '<li><input type="checkbox" checked>')
        html = html.replace("<li>\n<p>[x] ", '<li><p><input type="checkbox" checked>')

    return html


import json
api_token = ""
def get_api_token():
    global api_token
    if not api_token:
        with open(f"{settings.JOPLIN_JOPLIN_PATH}/settings.json") as joplin_settings:
            settings_json = json.load(joplin_settings)
            api_token = settings_json["api.token"]
    return api_token