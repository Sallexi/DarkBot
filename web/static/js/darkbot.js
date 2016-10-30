var darkbot = {};
darkbot.navSelector = function (id) {
    $("nav ul li").removeClass("active");
    $('#' + id).addClass('active');
};

darkbot.toggleSidebar = function () {
    var leftPanel = $('#left-panel');
    var centerPanel = $('#center-panel');
    var arrow = $('#arrow');

    leftPanel.toggleClass('minimized');
    centerPanel.toggleClass('expanded');
    arrow.toggleClass('arrow-right');

    if (leftPanel.hasClass('minimized')) {
        Cookies.set('nav_minimized', true);
    } else {
        Cookies.set('nav_minimized', false);
    }
};

darkbot.toggleCookie = function (cookie) {
    if (Cookies.get(cookie) === "true") {
        Cookies.set(cookie, false);
    } else {
        Cookies.set(cookie, true);
    }
};