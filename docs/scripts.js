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

    let lockedLayer = null;
    let currentHoverLayer = null;

    const defaultView = document.getElementById("sidebar-default-view");
    const detailView = document.getElementById("sidebar-detail-view");
    const resetBtn = document.getElementById("sb-reset-btn");
    const lockStatusBadge = document.getElementById("sb-lock-status");

    // Styling constants for district highlighting
    const HIGHLIGHT_STYLE = {
        weight: 3.5,
        color: "#ffffff",
        dashArray: "",
        fillOpacity: 0.95
    };

    function formatPct(val) {
        if (val === undefined || val === null || isNaN(val)) return "N/A";
        return (parseFloat(val) * 100).toFixed(1) + "%";
    }

    function populateSidebar(props) {
        if (!props) return;

        defaultView.style.display = "none";
        detailView.style.display = "block";

        // District Title & Codes
        document.getElementById("sb-detail-district-title").textContent = props.District || "District";
        document.getElementById("sb-detail-status").textContent = props.Targeted
            ? "Targeted / Redrawn Boundary"
            : "Existing Congressional District";

        // Lean Metrics
        const bln = document.getElementById("sb-detail-blended-lean");
        bln.textContent = props["Partisan Index"] !== undefined
            ? (props["Partisan Index"] > 0 ? `D +${(props["Partisan Index"] * 100).toFixed(1)}%` : `R +${(Math.abs(props["Partisan Index"]) * 100).toFixed(1)}%`)
            : (props["Margin Partisan"] || "EVEN");

        document.getElementById("sb-detail-pres-margin").textContent = props["Margin New Partisan"] || props["Margin Partisan"] || "EVEN";

        // 2024 Representative Info & Race Edge Cases
        const repName = props.House_Winner || "Contested / Open Seat";
        const repParty = (props.House_Party || "IND").toUpperCase();
        const raceType = props.House_Race_Type || "Standard Contest";
        const incText = props.House_Incumbent ? "Incumbent" : "Challenger / Open";

        document.getElementById("sb-detail-rep-name").textContent = repName;
        document.getElementById("sb-detail-rep-type").textContent = `${incText} • ${raceType}`;

        const houseMarginEl = document.getElementById("sb-detail-house-margin");
        if (raceType.includes("Unopposed") || raceType.includes("Uncontested")) {
            houseMarginEl.textContent = "Unopposed";
        } else if (raceType.includes("D_vs_D") || raceType.includes("R_vs_R")) {
            houseMarginEl.textContent = `${props.House_Margin ? Math.abs(props.House_Margin * 100).toFixed(1) + '%' : 'Same-Party'}`;
        } else {
            houseMarginEl.textContent = props.House_Margin
                ? (props.House_Margin > 0 ? `D +${(props.House_Margin * 100).toFixed(1)}%` : `R +${Math.abs(props.House_Margin * 100).toFixed(1)}%`)
                : "N/A";
        }

        const indicator = document.getElementById("sb-house-party-indicator");
        indicator.className = "party-indicator " + (repParty.startsWith("D") ? "dem" : repParty.startsWith("R") ? "rep" : "");

        // Racial Demographics
        document.getElementById("sb-detail-total-vap").textContent = `Total VAP: ${(props.TotalVAP || 0).toLocaleString()}`;
        document.getElementById("sb-detail-hispanic-pct").textContent = formatPct(props.HispanicPct);
        document.getElementById("sb-detail-white-pct").textContent = formatPct(props.WhitePct);
        document.getElementById("sb-detail-black-pct").textContent = formatPct(props.BlackPct);
        document.getElementById("sb-detail-asian-pct").textContent = formatPct(props.AsianPct);
        document.getElementById("sb-detail-native-pct").textContent = formatPct(props.NativePct);
    }

    function resetSidebar() {
        if (lockedLayer && window._choroplethLayer) {
            window._choroplethLayer.resetStyle(lockedLayer);
        }
        if (currentHoverLayer && window._choroplethLayer) {
            window._choroplethLayer.resetStyle(currentHoverLayer);
        }
        lockedLayer = null;
        currentHoverLayer = null;
        detailView.style.display = "none";
        defaultView.style.display = "block";
    }

    if (resetBtn) {
        resetBtn.addEventListener("click", resetSidebar);
    }

    // Attach to Leaflet instances once ready
    function setupLayerEvents() {
        const mapEl = document.querySelector(".folium-map");
        if (!mapEl) return;
        const map = window[mapEl.id];
        if (!map) return setTimeout(setupLayerEvents, 150);

        map.eachLayer(function (layer) {
            // Find the active GeoJson vector choropleth layer
            if (layer.eachLayer && layer.feature || (layer instanceof L.GeoJSON)) {
                window._choroplethLayer = layer;

                layer.eachLayer(function (featureLayer) {
                    featureLayer.on({
                        mouseover: function (e) {
                            if (lockedLayer) return; // Ignore hover events while locked
                            currentHoverLayer = e.target;
                            currentHoverLayer.setStyle(HIGHLIGHT_STYLE);
                            if (!L.Browser.ie && !L.Browser.opera && !L.Browser.edge) {
                                currentHoverLayer.bringToFront();
                            }
                            lockStatusBadge.textContent = "Hovering (Click to Lock)";
                            lockStatusBadge.classList.remove("locked");
                            populateSidebar(e.target.feature.properties);
                        },
                        mouseout: function (e) {
                            if (lockedLayer) return;
                            if (currentHoverLayer) {
                                layer.resetStyle(currentHoverLayer);
                                currentHoverLayer = null;
                            }
                            resetSidebar();
                        },
                        click: function (e) {
                            // Toggle lock state
                            if (lockedLayer === e.target) {
                                // Unlock if clicked a second time
                                layer.resetStyle(lockedLayer);
                                lockedLayer = null;
                                lockStatusBadge.textContent = "Hovering (Click to Lock)";
                                lockStatusBadge.classList.remove("locked");
                                resetSidebar();
                            } else {
                                // Lock onto new district
                                if (lockedLayer) layer.resetStyle(lockedLayer);
                                lockedLayer = e.target;
                                lockedLayer.setStyle(HIGHLIGHT_STYLE);
                                lockedLayer.bringToFront();
                                lockStatusBadge.textContent = "Locked District Selection";
                                lockStatusBadge.classList.add("locked");
                                populateSidebar(e.target.feature.properties);
                            }
                        }
                    });
                });
            }
        });
    }

    setupLayerEvents();

    // Directly attach to body (nested DOMContentLoaded listener removed)
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true
    });
});
