document.addEventListener("DOMContentLoaded", function () {

    // 1. Navigation Management
    (function manageNavigation() {
        const navContainer = document.querySelector(".map-page-navigation");
        if (!navContainer) return;

        const currentPath = window.location.pathname.split("/").pop();
        const activePage = (currentPath === "" || currentPath === "index.html") ? "index.html" : currentPath;

        navContainer.setAttribute("data-current-page", activePage);
        const targetLink = navContainer.querySelector(`a[href="${activePage}"]`);
        if (targetLink) {
            targetLink.classList.add("active");
        }
    })();

    // 2. Format Legend Ticks
    var checkTicksInterval = setInterval(function () {
        var ticks = document.querySelectorAll('div.legend g.tick text');
        if (ticks.length > 0) {
            clearInterval(checkTicksInterval);
            var customLabels = ['-40%', '-20%', '0%', '+20%', '+40%'];
            for (var i = 0; i < ticks.length; i++) {
                if (i < customLabels.length) {
                    ticks[i].textContent = customLabels[i];
                }
            }
        }
    }, 100);

    // 3. Populate Vote Margin Fill Bars from data-width
    document.querySelectorAll('.bar-fill[data-width]').forEach((el) => {
        const w = el.getAttribute('data-width');
        if (w) el.style.width = w;
    });

    // 4. Sidebar Toggle Listener (Delegated to handle all screen sizes)
    document.addEventListener('click', function (e) {
        const toggleBtn = e.target.closest('#sidebar-toggle');
        if (toggleBtn) {
            e.preventDefault();
            e.stopPropagation();
            const sidebar = document.getElementById('sidebar');
            if (sidebar) {
                sidebar.classList.toggle('collapsed');
            }
        }
    });
});
