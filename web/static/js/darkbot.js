var darkbot = {};

darkbot.navSelector = function (id) {
    $("nav ul li").removeClass("active");
    $('#' + id).addClass('active');
};