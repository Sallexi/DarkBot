var darkbot = {};

darkbot.navSelector = function (id) {
    $("nav ul li").removeClass("active");
    $('#' + id).addClass('active');
};

darkbot.toggleSidebar = function () {
    $('#left-panel').toggleClass('minimized');
    $('#center-panel').toggleClass('expanded');
    $('#arrow').toggleClass('arrow-right');
};