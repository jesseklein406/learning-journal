$(document).ready(function() {
  $("input").eq(1).on("click", function(e) {
    e.preventDefault();
    $.ajax({
      type: "POST",
      url: "add",
      data: {
        title: $("input").first().val(),
        content: $("textarea").first().val(),
      }
    }).done(function() {
      $('#message').html('Successfully submitted!');
    });
  });
});
