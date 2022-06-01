function render_latex(element) {

    // content.html("toto");

    renderMathInElement(element, {
      // customised options
      // • auto-render specific keys, e.g.:
      delimiters: [
        {left: "$$", right: "$$", display: true},
        {left: '$', right: '$', display: false},
        {left: "\\(", right: "\\)", display: false},
        {left: "\\begin{equation}", right: "\\end{equation}", display: true},
        {left: "\\begin{align}", right: "\\end{align}", display: true},
        {left: "\\begin{alignat}", right: "\\end{alignat}", display: true},
        {left: "\\begin{gather}", right: "\\end{gather}", display: true},
        {left: "\\begin{CD}", right: "\\end{CD}", display: true},
        {left: "\\[", right: "\\]", display: true}
        ],
      // • rendering keys, e.g.:
      throwOnError: false,
    });

    let jquery_element = $(element);
    // replace dollar placeholder in <code></code>:
    jquery_element.find("code").each(function (el) {
      let code = $(this);
      code.html((index, html) => {
        return html.replaceAll("@@ANTISLASH_DOLLAR_PALCEHOLDER@@", "\\$");
      });
    });
    
    // replace dollar placeholder elsewhere
    jquery_element.html((index, html) => {
      return html.replaceAll("@@ANTISLASH_DOLLAR_PALCEHOLDER@@", "$");
    });

}
