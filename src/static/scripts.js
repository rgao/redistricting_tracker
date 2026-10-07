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

    // 5. Dynamic Tooltip Color-Coding
    function colorizeTooltip(tooltipElement) {
        if (!tooltipElement) return;

        const cells = tooltipElement.querySelectorAll("td");
        cells.forEach((td) => {
            const text = td.textContent.trim();

            // Democratic / Harris advantage
            if (text.startsWith("Harris+") || text.startsWith("D +") || text.startsWith("D+")) {
                td.style.color = "#2563eb"; // Blue
                td.style.fontWeight = "bold";
            }
            // Republican / Trump advantage
            else if (text.startsWith("Trump+") || text.startsWith("R +") || text.startsWith("R+")) {
                td.style.color = "#dc2626"; // Red
                td.style.fontWeight = "bold";
            }
            // Neutral / Even
            else if (text === "EVEN") {
                td.style.color = "#64748b"; // Slate Grey
                td.style.fontWeight = "bold";
            }
        });
    }

    // Observe Leaflet map container for inserted and re-rendered tooltip contents
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) {
                    if (node.classList.contains("leaflet-tooltip")) {
                        colorizeTooltip(node);
                    } else {
                        const nested = node.querySelector(".leaflet-tooltip");
                        if (nested) colorizeTooltip(nested);
                    }
                }
            });

            // Handle in-place text updates when dragging cursor over adjacent boundaries
            if (mutation.type === "characterData" || mutation.type === "childList") {
                const targetTooltip = mutation.target.nodeType === 1 
                    ? mutation.target.closest(".leaflet-tooltip") 
                    : mutation.target.parentElement?.closest(".leaflet-tooltip");
                if (targetTooltip) {
                    colorizeTooltip(targetTooltip);
                }
            }
        });
    });

    // Directly attach to body (nested DOMContentLoaded listener removed)
    observer.observe(document.body, { 
        childList: true, 
        subtree: true, 
        characterData: true 
    });
});
