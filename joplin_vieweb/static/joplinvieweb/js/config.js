$(document).ready(function () {
    
    /**
     * Submit ajax request
     */
    $("#config_form").submit(function (event) {
        event.preventDefault();
        $("body").addClass("loading");
        $.ajax({
            type: "POST",
            url: "/joplin/config/",
            headers: { "X-CSRFToken": csrftoken },
            data: $(this).serialize(),
            success: (data) => { 
                $("body").removeClass("loading");
                if (!data["status"]) {
                    display_error(data["message"]);
                }
                else {
                    $("#config_joplin_popup_save_success").modal({ fadeDuration: 100 });
                } 
            },
            error: (err) => { $("body").removeClass("loading"); display_error(err); },
            complete: () => { $("body").removeClass("loading"); }
        });
        return false;
    });
    
    /**
     * Click on test
     */
    $("#test_btn").click(() => {
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
                    display_error(data["message"]);
                }
                else {
                    $("#config_joplin_popup_test_success").modal({ fadeDuration: 100 });
                }
            },
            error: (err) => { $("body").removeClass("loading"); display_error(err); },
            complete: () => { $("body").removeClass("loading"); }
        });
    });

    /**
     * On target combo changed
     */
     $("#id_target").change((event) => {
        form_fields(event.target.value);
         
     });

     /**
      * Init form_fields enable
      */
      form_fields($("#id_target").val());
});

function form_fields(selected_value) {
    let fields = $("#config_fields");
    let test_btn = $("#test_btn");
    if (selected_value != "5") {
       fields.addClass("disabled");
       test_btn.prop("disabled",true)
       fields.find(":input").attr("disabled", true);
       
    }
    else {
        fields.removeClass("disabled");
        test_btn.prop("disabled",false)
        fields.find(":input").attr("disabled", false);
    }
}

function display_error(message) {
    $("#config_joplin_popup_error p").html(message);
    $("#config_joplin_popup_error").modal({ fadeDuration: 100 });
}