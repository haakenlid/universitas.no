$(function(){
  $('.slideshow').slick({ dots:true, arrows:true });
  $('.tingo').html(function(i, v) {
    return v.replace(
      /(^.{10}\S*)/,
      '<span class="inngangsord">$1</span>'
    );
  });

});
