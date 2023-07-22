/**
 * Class to display the search "note" and manage it.
 * 
 * Emits:
 *  - "display search note", param: html_data
 * - 'note_notebook_selected', param: [note_id, notebook_id]
 */
class Search extends EventEmitter {
    constructor() {
        super();
        this._searching = false;
    }

    search_ongoing() {
        return (($("#search_btn").length !== 0) || this._searching);
    }

    /**
     * Get html on server and notify the content to noteView.
     */
    init() {
        $.get(
            '/joplin/search_html',
            (data) => { this.display_search_page(data); }
            );
    }

    /**
     * Display search page (data get from server) and attach to events
     */
    display_search_page(data) {
        this.emit("display search note", data);
        let search_input = $("#search_input");

        // give focus to input:
        search_input.focus();

        // register search button click
        $("#search_btn").on("click", () => {
            this.search(search_input.val());
        });

        // register enter key in add tag input:
        search_input.keyup((e) => {
            if (e.keyCode == 13) {
                this.search(search_input.val());
            }
        });

        // register click on result
        $(".search_result").off();
        $(".search_result").on("click", (ev) => {
            let note_id = $(ev.currentTarget).data('note-id');
            let notebook_id = $(ev.currentTarget).data('notebook-id');
            super.emit("note_notebook_selected", [note_id, notebook_id]);
        });
    }
    
    /**
     * Do the search on server.
     */
    search(search_value) {
        this._searching = true;
        display_progress($("#note_view"));
        $.ajax({
            url: '/joplin/search/' + btoa(search_value),
            type: 'post',
            headers: { "X-CSRFToken": csrftoken },
            data: JSON.stringify({ "_": "_" }),
            success: (data) => {
                this._searching = false;
                clear_progress($("#note_view"));
                this.display_search_page(data);
            },
            error: () => { 
                this.init();
                this._searching = false;
                alert("Search fail");
            },
        })
    }
}