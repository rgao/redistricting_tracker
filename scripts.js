document.addEventListener("DOMContentLoaded", function() {
    
    // 1. Dynamic Page Navigation Active State Manager
    (function manageNavigation() {
        const navContainer = document.querySelector(".map-page-navigation");
        if (!navContainer) return;

        // Isolate the base filename from the URL path string
        const currentPath = window.location.pathname.split("/").pop();
        
        // Fallback default target context for root-level domain structures
        const activePage = (currentPath === "" || currentPath === "index.html") ? "index.html" : currentPath;

        // Apply visual markers and styling hooks to target links
        navContainer.setAttribute("data-current-page", activePage);
        
        const targetLink = navContainer.querySelector(`a[href="${activePage}"]`);
        if (targetLink) {
            targetLink.classList.add("active");
        }
    })();


    // 2. Format Legend Ticks with Clean Percentage Text
    var checkTicksInterval = setInterval(function() {
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

});
