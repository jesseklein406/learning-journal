$(document).ready(function() {
  $("input").eq(2).on("click", function(e) {
    e.preventDefault();
    $.ajax({
      type: "POST",
      url: "commit",
      data: {
        title: $("input").first().val(),
        content: $("textarea").first().val(),
        id: $("input").eq(1).val()
      }
    }).done(function() {
      $('#message').html('Changes saved!');
    });
  });
});
