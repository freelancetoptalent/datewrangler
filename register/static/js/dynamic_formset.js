function forloop_counter(row){
  $('div.person-form').each(function(index){
    $('.forloop-counter', this).text(index + 1);
  });
}

$(function() {
  $('div.person-form').formset({
    added: forloop_counter,
    removed: forloop_counter
  });
});
