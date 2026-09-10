document.addEventListener("DOMContentLoaded", function() {
    
    // Navigation Management
    (function manageNavigation() {
        const navContainer = document.querySelector(".map-page-navigation");
        if (!navContainer) return;

        // Isolate page URL
        const currentPath = window.location.pathname.split("/").pop();
        
        // Fallback default target 
        const activePage = (currentPath === "" || currentPath === "index.html") ? "index.html" : currentPath;

        // Active page styling
        navContainer.setAttribute("data-current-page", activePage);
        
        const targetLink = navContainer.querySelector(`a[href="${activePage}"]`);
        if (targetLink) {
            targetLink.classList.add("active");
        }
    })();

    // Format Legend Ticks 
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

    // Sidebar loading
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-btn');

    toggleBtn.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
    });
});

