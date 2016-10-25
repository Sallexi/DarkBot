function navSelector(id) {
    $("nav ul li").removeClass("active");
    $('#' + id)
        .addClass('active')
        .parent('div').addClass('in');
}