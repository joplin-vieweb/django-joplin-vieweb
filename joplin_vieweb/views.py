from django.http.response import HttpResponseNotFound
from joplin_vieweb.edit_session import EditSession
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.conf import settings
from django.http import JsonResponse

from joplin_vieweb.forms import ConfigForm
from .joplin import Joplin
import json
from bs4 import BeautifulSoup
from pathlib import Path
import mimetypes
from .utils import mimetype_to_icon, markdown_public_ressource, md_to_html
from .lasts_notes import LastsNotes
import glob
import base64
from . import hyperlink_preview_cache


def conditional_decorator(dec, condition):
    def decorator(func):
        if not condition:
            # Return the function unchanged, not decorated.
            return func
        return dec(func)
    return decorator


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def index(request):
    return render(request, 'joplinvieweb/index.html')


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def notebooks(request):
    joplin = Joplin()
    joplin.parse_notebooks()
    data = json.dumps(joplin.rootNotebook.children, default=lambda o: o.__dict__, indent=4)
    return HttpResponse(data)


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def notes(request, notebook_id):
    joplin = Joplin()
    if request.method == "GET":  # list the notes of this notebook
        notes_metadata = joplin.get_notes_metadata(notebook_id)
        return render(request, 'joplinvieweb/notes_list.html', {"notes_metadata": notes_metadata})
    if request.method == "POST":  # create a notebook
        data = json.loads(request.body)
        title = data["title"]
        parent_id = data["parent_id"]
        if parent_id == "0":
            parent_id = ""
        new_notebook_id = joplin.create_notebook(parent_id, title)
        return HttpResponse(new_notebook_id)


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def notebook_delete(request, notebook_id):
    if request.method == "POST":  # delete the notebook
        joplin = Joplin()
        if notebook_id:
            # first get all the notes of that notebook (recursively, pffff ;-) ) to remove them from last notes:
            notes_metadata = joplin.get_notes_metadata_recursive(notebook_id)
            LastsNotes.delete_notes([one_note.id for one_note in notes_metadata])
            joplin.delete_notebook(notebook_id)
        return HttpResponse("")
    return HttpResponseNotFound("")


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def notebook_rename(request, notebook_id):
    if request.method == "POST":  # rename the notebook
        data = json.loads(request.body)
        title = data["title"]
        joplin = Joplin()
        joplin.rename_notebook(notebook_id, title)
        return HttpResponse("")
    return HttpResponseNotFound("")


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def note(request, note_id, format="html"):
    return HttpResponse(note_body_name(note_id, format)[0])


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def note_notebook(request, note_id):
    return HttpResponse(Joplin().get_note_notebook(note_id))


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def delete_note(request, note_id):
    joplin = Joplin()
    joplin.delete_note(note_id)
    LastsNotes.delete_note(note_id)
    return HttpResponse("")


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def render_markdown(request):
    try:
        if request.method == "POST":
            md = json.loads(request.body)
            md = md["markdown"]
            html = md_to_html(md, True)
            return HttpResponse(html)
    except:  # noqa E722
        pass
    return HttpResponseNotFound('')


def note_body_name(note_id, format, public=False):
    note_body, note_name, is_todo, todo_completed = Joplin().get_note_body_name_istodo(note_id)

    if public:
        note_body = markdown_public_ressource(note_body)

    if format == "md":
        return (note_body, note_name, is_todo)

    note_body = '[TOC]\n\n' + note_body
    html = md_to_html(note_body, False)

    # Finally we set an attachment image to the attachments
    # We search for <a href="/joplin/joplin_ressources"> or <a href=":/">
    soup = BeautifulSoup(html)
    for link in soup.findAll('a'):
        if "joplin_ressources" in link.get('href') or ":/" == link.get('href')[0:2]:
            mime_type_guess = mimetypes.guess_type(link.get_text())
            img = soup.new_tag("span", **{'class': mimetype_to_icon(mime_type_guess)})
            br = soup.new_tag("br")
            link.insert(0, br)
            link.insert(0, img)
            link['class'] = link.get('class', []) + ['attachment_link']
        link['target'] = '_blank'

    toc_item = soup.find('div', {"class": "toc"})
    if toc_item:
        for one_link in toc_item.findAll('a'):
            current_href = str(one_link['href'])
            new_link = "javascript:scroll_to('" + current_href + "');"
            one_link['href'] = new_link
            one_link['target'] = ""
    html = str(soup)

    LastsNotes.set_last(note_id, note_name, is_todo, todo_completed)

    return (html, note_name)


def public_note(request, note_id):
    joplin = Joplin()
    tags = joplin.get_note_tags(note_id)
    if "public" in [tag.name for tag in tags]:
        return render(request, 'joplinvieweb/public_note.html', {"note_id": note_id})
    return HttpResponse("not a public note")


def public_note_data(request, note_id):
    joplin = Joplin()
    tags = joplin.get_note_tags(note_id)
    if "public" in [tag.name for tag in tags]:
        body, name, is_todo = note_body_name(note_id, format="html", public=True)
    return HttpResponse(json.dumps({"name": name, "body": body, "is_todo": is_todo}))


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def note_checkboxes(request, note_id):
    cb = json.loads(request.body)
    cb = cb["cb"]
    Joplin().update_note_checkboxes(note_id, cb)
    return HttpResponse("")


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def pin_note(request, note_id):
    if request.method == "POST":
        LastsNotes.pin_note(note_id, True)
        return HttpResponse("")


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def unpin_note(request, note_id):
    if request.method == "POST":
        LastsNotes.pin_note(note_id, False)
        return HttpResponse("")


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def note_tags(request, note_id):
    joplin = Joplin()
    if request.method == "GET":
        note_tags = joplin.get_note_tags(note_id)
        return HttpResponse(json.dumps([one_tag.name for one_tag in note_tags]))
        # return render(request, 'joplinvieweb/note_tags.html', {"note_tags": note_tags})
    if request.method == "POST":
        tags = json.loads(request.body)
        tags = tags["tags"]
        joplin.update_note_tags(note_id, tags)
        return HttpResponse("")


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def mark_todo(request, note_id):
    joplin = Joplin()
    if request.method == "POST":
        data = json.loads(request.body)
        completed: bool = data["completed"]
        note_name = data["note_name"]
        joplin.mark_todo(note_id, completed)
        LastsNotes.set_last(note_id, note_name, True, completed)
        return HttpResponse("")

@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def notebooks_error(request):
    return render(request, 'joplinvieweb/notebooks_error.html', {})


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def notebook_error(request, notebook_id):
    return render(request, 'joplinvieweb/notebook_error.html', {"notebook_id": notebook_id})


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def tag_notes_error(request, tag_id):
    return render(request, 'joplinvieweb/tag_notes_error.html', {"tag_id": tag_id})


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def note_error(request):
    return render(request, 'joplinvieweb/note_error.html', {})


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def joplin_ressource(request, ressource_path):
    return joplin_public_ressource(request, ressource_path)


def joplin_public_ressource(request, ressource_path):
    try:
        joplin = Joplin()
        name = joplin.get_ressource_name(ressource_path)
        ressources_path = f"{settings.JOPLIN_JOPLIN_PATH}/resources/"
        file_path = Path(ressources_path) / Path(ressource_path)
        file_path = glob.glob("{}*".format(file_path))[0]
        file_path = Path(file_path)
        mime_type_guess = mimetypes.guess_type(file_path.name)
        ressource_file = open(file_path, 'rb')
        if not name:
            name = file_path.name
        headers = {}
        headers["Content-Disposition"] = 'inline; filename="' + name + '"'
        if mime_type_guess is not None:
            response = HttpResponse(content=ressource_file, content_type=mime_type_guess[0], headers=headers)
        else:
            response = HttpResponse(content=ressource_file, headers=headers)
    except IOError:
        response = HttpResponseNotFound("")

    return response


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def tags_error(request):
    return render(request, 'joplinvieweb/tags_error.html', {})


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def tags(request):
    joplin = Joplin()
    tags = joplin.get_tags(with_notes=True)
    return render(request, 'joplinvieweb/tags_list.html', {"tags": tags})


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def all_tags(request):
    joplin = Joplin()
    tags = joplin._get_tags()
    return HttpResponse(json.dumps(tags))


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def tag_notes(request, tag_id):
    joplin = Joplin()
    notes_metadata = joplin.get_notes_metadata_from_tag(tag_id)
    return render(request, 'joplinvieweb/notes_list.html', {"notes_metadata": notes_metadata})


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def sync_data(request):
    joplin = Joplin()
    joplin.get_synch()
    return HttpResponse(json.dumps(joplin.get_synch()))


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def do_sync(request):
    joplin = Joplin()
    joplin.start_synch()
    return HttpResponse("Sync started")


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def upload_note_attachment(request, session_id):
    if request.method == 'POST':
        for key, value in request.FILES.items():
            attachment_id = EditSession.save_file(session_id, value)
            return HttpResponse(json.dumps({"data": {"filePath": "/joplin/edit_session_ressource/"
                                                     "{}/{}".format(session_id, attachment_id)}}))


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def edit_session(request):
    if request.method == 'POST':
        session_id = EditSession.create_session()
        return HttpResponse(session_id)


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def edit_session_ressource(request, session_id, file):
    try:
        ressources_path = EditSession.get_path(session_id)
        file_path = ressources_path / file
        mime_type_guess = mimetypes.guess_type(file_path.name)
        ressource_file = open(file_path, 'rb')
        if mime_type_guess is not None:
            response = HttpResponse(
                content=ressource_file, content_type=mime_type_guess[0])
        else:
            response = HttpResponse(content=ressource_file)
    except IOError:
        response = HttpResponseNotFound("")

    return response


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def edit_session_update_note(request, session_id, note_id):
    if request.method == 'POST':
        note_data = json.loads(request.body)
        # md = str(request.body.decode('utf-8'))
        md = note_data["markdown"]
        title = note_data["title"]
        is_todo = True if note_data["is_todo"] == 1 else False
        md = EditSession.create_ressources_and_replace_md(session_id, md)
        joplin = Joplin()
        joplin.update_note(note_id, title, md, is_todo)

    return HttpResponse()


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def edit_session_create_note(request, session_id, notebook_id):
    if request.method == 'POST':
        note_data = json.loads(request.body)
        # md = str(request.body.decode('utf-8'))
        md = note_data["markdown"]
        title = note_data["title"]
        is_todo = True if note_data["is_todo"] == 1 else False
        md = EditSession.create_ressources_and_replace_md(session_id, md)
        joplin = Joplin()
        note_id = joplin.create_note(notebook_id, title, md, is_todo)

    return HttpResponse(note_id)


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def get_lasts_notes(request):
    return HttpResponse(LastsNotes.read_lasts_notes())


def get_hyperlink_preview(request, link):
    link = base64.b64decode(link.replace("_", "/").replace("-", "+")).decode('utf-8')
    data = hyperlink_preview_cache.get_hyperlink_preview(link)
    if data is None:
        return HttpResponseNotFound("")
    return HttpResponse(json.dumps(data))


def get_hyperlink_preview_image(request, link):
    link = base64.b64decode(link.replace("_", "/").replace("-", "+")).decode('utf-8')
    data = hyperlink_preview_cache.get_hyperlink_preview_image(link)
    if data is None:
        return HttpResponseNotFound("")
    return HttpResponse(json.dumps(data))


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def config(request):
    joplin = Joplin()
    if request.method == 'GET':
        config = joplin.get_config()
        config["username"] = config["user"]
        for key, value in config.items():
            if value == ".":
                config[key] = ""
        config_form = ConfigForm(config)
        return render(request, 'joplinvieweb/config.html', {"form": config_form})

    if request.method == 'POST':
        config_form = ConfigForm(request.POST)
        supported_targets = ["5", "6",  "8", "9"]
        if not config_form.data["target"] in supported_targets:
            try:
                joplin.set_config({"target": "0", "path": ".", "username": ".", "password": ".", "interval": "0"})
                return JsonResponse({"status": True})
            except Exception as e:
                return JsonResponse({"status": False, "message": str(e)})
        if config_form.is_valid():
            try:
                joplin.set_config(config_form.cleaned_data)
                return JsonResponse({"status": True})
            except Exception as e:
                return JsonResponse({"status": False, "message": str(e)})
        else:
            return JsonResponse({
                                    "status": False,
                                    "message": "data are not valid: " + str(config_form.errors)
                                })


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def config_test(request):
    if request.method == 'POST':
        joplin = Joplin()
        config_form = ConfigForm(request.POST)
        if config_form.is_valid():
            try:
                ret = joplin.test_config(config_form.cleaned_data)
                return JsonResponse(ret)
            except Exception as e:
                return JsonResponse({"status": False, "message": str(e)})
        else:
            return JsonResponse({"status": False, "message": f"Invalid data:\n{config_form.errors}"})


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def joplin_logout(request):
    logout(request)


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def search_html(request):
    return render(request, 'joplinvieweb/search.html', {})


@conditional_decorator(login_required, settings.JOPLIN_LOGIN_REQUIRED)
def search(request, query):
    """_summary_
    Returns:
    html to display the search result
        
    """
    if request.method != 'POST':
        return JsonResponse({"status": False, "message": f"Unexpected request method {request.method}"})

    search_value = base64.b64decode(query).decode('utf-8').strip()
    joplin = Joplin()
    res = joplin.search(search_value)
    # res: [{'id': , 'parent_id': , 'title': , 'notebook_title': },}, {...}, ...]
    return render(request, 'joplinvieweb/search.html', {'found': res, 'search': search_value})
