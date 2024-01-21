class Configuration {
    init() {
        $("#config_form").submit((event) => { this.submit(event); })
        $("#test_btn").click(() => { this.test() });


        /**
         * On target combo changed
         */
        this.current_target = $("#id_target").val();
        if (this.current_target != "8") {
            $("#config_s3_fields").hide();
        }
        $("#id_target").change((event) => {
            this.form_fields(event.target.value);
            
        });

        /**
         * Init form_fields enable
         */
        this.form_fields($("#id_target").val());
    }

    /**
     * Submit
     */
    submit(event) {
        event.preventDefault();
        $("body").addClass("loading");
        $.ajax({
            type: "POST",
            url: "/joplin/config/",
            headers: { "X-CSRFToken": csrftoken },
            data: $("#config_form").serialize(),
            success: (data) => { 
                $("body").removeClass("loading");
                if (!data["status"]) {
                    this.display_error(data["message"]);
                }
                else {
                    $("#config_joplin_popup_save_success").modal({ fadeDuration: 100 });
                } 
            },
            error: (err) => { $("body").removeClass("loading"); this.display_error(err); },
            complete: () => { $("body").removeClass("loading"); }
        });
        return false;
    }

    /**
     * Test config
     */
    test() {
        console.log("test config");
        // Trig the browser validation
        let config_form = $("#config_form");
        if (!config_form[0].checkValidity()) {
            // If the form is invalid, submit it. The form won't actually submit;
            // this will just cause the browser to display the native HTML5 error messages.
            config_form.find(':submit').click();
            return;
        }

        $("body").addClass("loading");
        $.ajax({
            type: "POST",
            url: "/joplin/config/test/",
            headers: { "X-CSRFToken": csrftoken },
            data: $("#config_form").serialize(),
            success: (data) => {
                $("body").removeClass("loading");
                if (!data["status"]) {
                    this.display_error(data["message"]);
                }
                else {
                    $("#config_joplin_popup_test_success").modal({ fadeDuration: 100 });
                }
            },
            error: (err) => { $("body").removeClass("loading"); this.display_error(err); },
            complete: () => { $("body").removeClass("loading"); }
        });
    }

    /**
     * React to target selection change
     */
     form_fields(selected_value) {
        if (this.current_target != selected_value) {
            this.current_target = selected_value;
            $("#id_path").val("");
            $("#id_username").val("");
            $("#id_password").val("");
            if (this.current_target == "8") {
                $("#config_url_tip").html("");
                $("#config_s3_fields").show();
                $("#id_s3bucket").prop("required", true);
                $("#id_s3region").prop("required", true);
            }
            else {
                $("#config_url_tip").html("Url is like that: https://your.nextcloud.com/remote.php/dav/files/user/Documents/JoplinSynchro<br>");
                $("#config_s3_fields").hide();
                $("#id_s3bucket").prop("required", false);
                $("#id_s3region").prop("required", false);
            }
        }
        let fields = $("#config_fields");
        let test_btn = $("#test_btn");
        if ((selected_value != "5") && (selected_value != "9") && (selected_value != "6") && (selected_value != "8")) {
           fields.addClass("disabled");
           test_btn.prop("disabled",true)
           fields.find(":input").attr("disabled", true);
           
        }
        else {
            fields.removeClass("disabled");
            test_btn.prop("disabled",false)
            fields.find(":input").attr("disabled", false);
        }
        if (selected_value != "5") {
            $("#test_btn").hide();
        }
        else {
            $("#test_btn").show();
        }
    }

    /**
     * 
     */
     display_error(message) {
        $("#config_joplin_popup_error p").html(message);
        $("#config_joplin_popup_error").modal({ fadeDuration: 100 });
    }
}
