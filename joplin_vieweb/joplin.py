from typing import Optional

from joppy.api import Api
import logging
import json
import re
from django.conf import settings
from joplin_vieweb import joplin_x_api
from joplin_vieweb.utils import get_api_token


class Notebook():
    def __init__(self):
        self.id = "NO_ID"
        self.name = "NO_TITLE"
        self.children = []

    def __str__(self):
        return "{} [{}]\n    {}".format(self.name, self.id, str(self.children))

    def __repr__(self):
        return self.__str__()


class ReprJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'reprJSON'):
            return obj.reprJSON()
        else:
            return json.JSONEncoder.default(self, obj)


class NoteMetadata:
    def __init__(self):
        self.id = "NO_ID"
        self.name = "NO_NAME"
        self.is_todo: bool = False
        self.todo_completed: bool = False

    @classmethod
    def from_joppy(cls, joppy_note):
        note = cls()
        note.id = joppy_note["id"]
        note.name = joppy_note["title"]
        note.is_todo = joppy_note["is_todo"] == 1
        note.todo_completed = joppy_note["todo_completed"] != 0
        return note

    def __str__(self):
        return "Note metadata: {} [{}], is todo: [{}]{}".format(
            self.name,
            self.id,
            self.is_todo,
            "" if not self.is_todo else f", completed: [{self.todo_completed}]"
        )


class Joplin:
    folders_by_parent_id = dict()

    def __init__(self, token: Optional[str] = None):
        token = token if token is not None else get_api_token()
        self.joplin = Api(
            token=token,
            url=settings.JOPLIN_DATA_API_URL
        )
        self.joplin_x_api = joplin_x_api.Api(url=settings.JOPLIN_X_API_URL)
        self.rootNotebook = None

    def parse_notebooks(self):
        self.rootNotebook = Notebook()
        self.rootNotebook.id = ""
        self.rootNotebook.name = "ROOT NOTEBOOK"

        folders_by_id = {}

        folders = self.joplin.get_all_notebooks()
        folders_by_id = {folder["id"]: folder for folder in folders}

        Joplin.folders_by_parent_id = dict()
        for one_folder in folders:
            parent_id = one_folder["parent_id"]
            if parent_id in Joplin.folders_by_parent_id.keys():
                Joplin.folders_by_parent_id[parent_id].append(one_folder)
            else:
                Joplin.folders_by_parent_id[parent_id] = [one_folder]
        logging.debug("folders_by_id = " + str(folders_by_id))
        logging.debug("folders_by_parent_id = " + str(Joplin.folders_by_parent_id))
        self.append_notebook(self.rootNotebook)

    def append_notebook(self, notebook):
        """
        append to notebook every notebook with parent_id
        """
        if notebook.id in Joplin.folders_by_parent_id.keys():
            for one_folder in Joplin.folders_by_parent_id[notebook.id]:
                new_notebook = Notebook()
                new_notebook.id = one_folder["id"]
                new_notebook.name = one_folder["title"]
                notebook.children.append(new_notebook)
                self.append_notebook(new_notebook)

    def create_notebook(self, parent_id, title):
        return self.joplin.add_notebook(title=title, parent_id=parent_id)

    def delete_notebook(self, notebook_id):
        notebook_id = self.joplin.delete_notebook(notebook_id)
        logging.debug("delete_notebook [{}]".format(notebook_id))

    def rename_notebook(self, notebook_id, title):
        self.joplin.modify_notebook(notebook_id, title=title)
        logging.debug(
            "rename_notebook [{}] / [{}]".format(notebook_id, title))

    def get_notebook_descendants(self, notebook_id):
        # return a list of notebooks ids: all notebooks that are descendents of notebook_id
        descendents = [notebook_id]
        descendents = descendents + self.__get_descendents(notebook_id)
        return descendents

    def __get_descendents(self, one_descendent):
        try:
            descendents = [one["id"] for one in Joplin.folders_by_parent_id[one_descendent]]
        except:  # noqa E722
            descendents = []
        for one_descendent in descendents:
            descendents = descendents + self.__get_descendents(one_descendent)
        return descendents

    def get_notes_metadata_recursive(self, notebook_id):
        """
        Return a list of NoteMetadata for all notes which have given notebook_id as direct or indirect ancestor.
        """
        descendents = self.get_notebook_descendants(notebook_id)

        notes_metadata = []
        # for one_note in self.joplin.get_all_notes():
        for one_note in self.joplin.get_all_notes(fields="id,title,parent_id,is_todo,todo_completed"):
            if one_note["parent_id"] in descendents:
                notes_metadata.append(NoteMetadata.from_joppy(one_note))
        return notes_metadata

    def get_notes_metadata(self, notebook_id):
        """
        Return a list of NoteMetadata for all notes which have given notebook_id as direct ancestor.
        """
        notes_metadata = []
        for one_note in self.joplin.get_all_notes(fields="id,title,parent_id,is_todo,todo_completed"):
            if one_note["parent_id"] == notebook_id:
                notes_metadata.append(NoteMetadata.from_joppy(one_note))
        return notes_metadata

    def get_note_notebook(self, note_id):
        return self.joplin.get_note(note_id)["parent_id"]

    def get_notes_metadata_from_tag(self, tag_id):
        """
        Returns:
            a list of NoteMetadata for all notes with the given tag.
        """
        notes_metadata = []
        for one_note in self.joplin.get_all_notes(tag_id=tag_id, fields="id,title,parent_id,is_todo,"
                                                                        "todo_completed"):
            notes_metadata.append(NoteMetadata.from_joppy(one_note))
        return notes_metadata

    def get_note_body_name_istodo(self, note_id):
        note = self.joplin.get_note(note_id, fields="body,title,is_todo")
        return (note["body"], note["title"], note["is_todo"] != 0)

    def get_note_tags(self, note_id):
        tags = []
        for one_tag in self.joplin.get_all_tags(note_id=note_id):
            new_tag_metadata = NoteMetadata()
            new_tag_metadata.id = one_tag["id"]
            new_tag_metadata.name = one_tag["title"]
            tags.append(new_tag_metadata)
        return tags

    def update_note_tags(self, note_id, tags):
        current_tags = self.get_note_tags(note_id)
        current_tags_dict = {tag.name: tag.id for tag in current_tags}
        current_tags_names = current_tags_dict.keys()

        all_tags = self.get_tags()
        all_tags_dict = {tag.name: tag.id for tag in all_tags}
        all_tags_names = all_tags_dict.keys()

        existing_tags_to_add = []
        new_tags_to_add = []
        existing_tags_to_delete = list(set(current_tags_names) - set(tags))

        for one in tags:
            if one not in current_tags_names:
                if one in all_tags_names:
                    existing_tags_to_add.append(one)
                else:
                    new_tags_to_add.append(one)

        for tag_to_delete in existing_tags_to_delete:
            self.joplin.delete_tag(all_tags_dict[tag_to_delete], note_id)

        for tag_to_add in existing_tags_to_add:
            self.joplin.add_tag_to_note(tag_id=all_tags_dict[tag_to_add], note_id=note_id)

        for tag_to_add in new_tags_to_add:
            tag_id = self.joplin.add_tag(title=tag_to_add)
            self.joplin.add_tag_to_note(tag_id=tag_id, note_id=note_id)

    def update_note_checkboxes(self, note_id, cb):
        note_body = self.joplin.get_note(note_id, fields="body")["body"]
        cb_indexes = [m.start() for m in re.finditer("- \[[ x]\] ", note_body)]
        for checked, cb_index in zip(cb, cb_indexes):
            cb_string = "- [ ] "
            if checked == 1:
                cb_string = "- [x] "
            note_body = note_body[0:cb_index] + cb_string + \
                        note_body[cb_index + len(cb_string):]
        self.joplin.modify_note(note_id, body=note_body)

    def _get_tags(self):
        """
        Get all tags
        """
        return self.joplin.get_all_tags()

    def get_tags(self, with_notes=False):
        tags = []
        all_tags = self._get_tags()
        for one_tag in all_tags:
            add_one_tag = True
            if with_notes:
                if not self.joplin.get_all_notes(tag_id=one_tag["id"]):
                    # if one_tag has no note, we don't add it.
                    add_one_tag = False
            if add_one_tag:
                new_tag_metadata = NoteMetadata()
                new_tag_metadata.id = one_tag["id"]
                new_tag_metadata.name = one_tag["title"]
                tags.append(new_tag_metadata)
        return tags

    def search(self, query):
        res = self.joplin.search_all(query=query)
        # Here res =
        # [
        #     {'id': 'dbd...083',
        #      'parent_id': '1b08...3c9ea',
        #      'title': '#27'},
        #     {...}
        # ]
        for one_res in res:
            parent_notebook = self.joplin.get_notebook(one_res['parent_id'])
            try:
                one_res['notebook_title'] = parent_notebook['title']
            except:  # noqa
                one_res['notebook_title'] = "?"
        return res

    def create_resource(self, file_path, title):
        res_id = self.joplin.add_resource(filename=file_path, title=title)
        return (res_id, title)

    def get_ressource_name(self, resource_id):
        return self.joplin.get_resource(resource_id)["title"]

    def update_note(self, note_id, title, md, is_todo):
        self.joplin.modify_note(note_id, title=title, body=md, is_todo=1 if is_todo else 0)

    def create_note(self, notebook_id, title, md, is_todo: bool):
        if not title:
            title = "Untitled"
        return self.joplin.add_note(parent_id=notebook_id, title=title, body=md, is_todo=1 if is_todo else 0)

    def delete_note(self, note_id):
        self.joplin.delete_note(note_id)

    def get_config(self):
        return self.joplin_x_api.get_conf()

    def _joplin_vieweb_to_joplin_conf(self, joplin_vw_conf):
        joplin_config = {}
        password: str = joplin_vw_conf["password"]
        if password.replace("*", ""):
            joplin_config["sync.password"] = password
        joplin_config["sync.target"] = joplin_vw_conf["target"]
        joplin_config["sync.path"] = joplin_vw_conf["path"]
        joplin_config["sync.username"] = joplin_vw_conf["username"]
        joplin_config["sync.interval"] = joplin_vw_conf["interval"]
        supported_target = ["0", "5", "6", "8", "9"]
        if not joplin_config["sync.target"] in supported_target:
            raise Exception("Only nextcloud, S3, WebDAV and joplin server targets are supported.")
        try:
            joplin_config["sync.s3bucket"] = joplin_vw_conf["s3bucket"]
            joplin_config["sync.s3region"] = joplin_vw_conf["s3region"]
        except:  # noqa
            pass
        return joplin_config

    def set_config(self, config_data):
        # config_data are cleaned_data of a valid ConfigForm
        joplin_config = self._joplin_vieweb_to_joplin_conf(config_data)
        return self.joplin_x_api.set_conf(joplin_config)

    def test_config(self, config_data):
        joplin_config = self._joplin_vieweb_to_joplin_conf(config_data)
        return self.joplin_x_api.test_conf(joplin_config).json()

    def start_synch(self):
        self.joplin_x_api.start_synch()

    def get_synch(self):
        return self.joplin_x_api.get_synch()


if __name__ == "__main__":
    from django.conf import settings

    settings.configure(
        JOPLIN_JOPLIN_PATH="/root/.config/joplin",
        JOPLIN_X_API_URL="http://localhost:8081",
        JOPLIN_DATA_API_URL="http://localhost:41184")

    j = Joplin(token="078ede90250d17e9fc57487352d704a2798fffb03fd2efcae04c9e87bf664310508fb3ef9beebc861fc0690f6704a928ebc19210e2a0b066a183614ab2c9fb41")
    j.parse_notebooks()
    print(j.rootNotebook)

    notes_md = j.get_notes_metadata_recursive("c253973bcd43415cac6aa1d750ec500e")
    for one_note_metadata in notes_md:
        print(str(one_note_metadata))

