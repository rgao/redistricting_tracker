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

    // 3. Populate Vote Margin Fill Bars
    document.querySelectorAll('.bar-fill[data-width]').forEach((el) => {
        const w = el.getAttribute('data-width');
        if (w) el.style.width = w;
    });

    // 4. Sidebar Toggle Listener
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
            if (text.startsWith("Harris+") || text.startsWith("D +") || text.startsWith("D+")) {
                td.style.color = "#2563eb";
                td.style.fontWeight = "bold";
            } else if (text.startsWith("Trump+") || text.startsWith("R +") || text.startsWith("R+")) {
                td.style.color = "#dc2626";
                td.style.fontWeight = "bold";
            } else if (text === "EVEN") {
                td.style.color = "#64748b";
                td.style.fontWeight = "bold";
            }
        });
    }

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

    // =========================================================================
    // 6. DISTRICT INTERACTIVE HIGHLIGHTING & LOCKING
    // =========================================================================
    let lockedLayer = null;
    let currentHoverLayer = null;

    const defaultView = document.getElementById("sidebar-default-view");
    const detailView = document.getElementById("sidebar-detail-view");
    const resetBtn = document.getElementById("sb-reset-btn");
    const lockStatusBadge = document.getElementById("sb-lock-status");

    // Hover: Vivid Amber Gold
    const HOVER_STYLE = {
        weight: 2.2,
        color: "#f59e0b",
        dashArray: "",
        fillOpacity: 0.88
    };

    // Locked: Mint Green
    const LOCKED_STYLE = {
        weight: 3.2,
        color: "#10b981",
        dashArray: "",
        fillOpacity: 0.94
    };

    function formatPct2(val) {
        if (val === undefined || val === null || isNaN(val)) return "N/A";
        return (parseFloat(val) * 100).toFixed(2) + "%";
    }

    function applyPartyColor(element, party) {
        element.classList.remove("dem", "rep");
        if (!party) return;
        const p = party.toUpperCase();
        if (p.startsWith("D")) element.classList.add("dem");
        else if (p.startsWith("R")) element.classList.add("rep");
    }

    function isNonStandardRace(raceType) {
        if (!raceType) return false;
        const rt = raceType.toLowerCase();
        return !(rt.includes("standard") && !rt.includes("non-standard"));
    }

    function populateSidebar(props) {
        if (!props) return;

        defaultView.style.display = "none";
        detailView.style.display = "block";

        const raceType = props.House_Race_Type || "Standard Contest";
        const hasEdgeCase = isNonStandardRace(raceType);

        // 1. Sidebar District Header
        document.getElementById("sb-detail-district-title").textContent = props.District_Name || props.District;
        // District Header & Status Caption
        const statusEl = document.getElementById("sb-detail-status");
        if (props.Targeted) {
            statusEl.textContent = "Redrawn District";
            statusEl.style.display = "block";
        } else {
            statusEl.textContent = "";
            statusEl.style.display = "none";
        }

        // 2. Partisan Profile
        const blnEl = document.getElementById("sb-detail-blended-lean");
        const presEl = document.getElementById("sb-detail-pres-margin");

        // Partisan Lean Index as signed number (e.g. D +8.57, R +55.89)
        const partisanLeanText = props.Partisan_Lean_Index || "EVEN";
        blnEl.textContent = partisanLeanText;
        applyPartyColor(blnEl, partisanLeanText.startsWith("D") ? "DEM" : partisanLeanText.startsWith("R") ? "REP" : null);

        // Presidential Margin to 2 decimal places
        const presMargin = props["Margin 24"];
        if (presMargin !== undefined && presMargin !== null && !isNaN(presMargin)) {
            const presPct = Math.abs(parseFloat(presMargin) * 100).toFixed(2);
            presEl.textContent = presMargin > 0 ? `Harris +${presPct}%` : `Trump +${presPct}%`;
            applyPartyColor(presEl, presMargin > 0 ? "DEM" : "REP");
        } else {
            presEl.textContent = props["Margin 24 Partisan"] || "EVEN";
        }

        // 3. 2024 House Election Results
        const repName = props.House_Winner || "Uncontested / No Data";
        const repParty = (props.House_Party || "OTHER").toUpperCase();

        document.getElementById("sb-detail-rep-name").textContent = repName;

        const raceTypeEl = document.getElementById("sb-detail-rep-type");
        if (hasEdgeCase) {
            raceTypeEl.textContent = `* ${raceType}`;
            raceTypeEl.style.display = "block";
        } else {
            raceTypeEl.textContent = "";
            raceTypeEl.style.display = "none";
        }

        const houseMarginEl = document.getElementById("sb-detail-house-margin");
        if (props.House_MOV_Raw !== undefined && props.House_MOV_Raw !== null && !isNaN(props.House_MOV_Raw)) {
            houseMarginEl.textContent = `+${(parseFloat(props.House_MOV_Raw) * 100).toFixed(2)}%`;
        } else {
            houseMarginEl.textContent = "N/A";
        }
        applyPartyColor(houseMarginEl, repParty);

        const indicator = document.getElementById("sb-house-party-indicator");
        indicator.className = "party-indicator prominent";
        applyPartyColor(indicator, repParty);

        // 4. Demographics (VAP) formatted to 2 decimal places
        document.getElementById("sb-detail-white-pct").textContent = formatPct2(props.WhitePct);
        document.getElementById("sb-detail-hispanic-pct").textContent = formatPct2(props.HispanicPct);
        document.getElementById("sb-detail-black-pct").textContent = formatPct2(props.BlackPct);
        document.getElementById("sb-detail-asian-pct").textContent = formatPct2(props.AsianPct);
        document.getElementById("sb-detail-minority-pct").textContent = formatPct2(props.MinorityPct);
    }

    function resetSidebar() {
        if (lockedLayer && window._mainGeoJsonLayer) {
            window._mainGeoJsonLayer.resetStyle(lockedLayer);
        }
        if (currentHoverLayer && window._mainGeoJsonLayer) {
            window._mainGeoJsonLayer.resetStyle(currentHoverLayer);
        }
        lockedLayer = null;
        currentHoverLayer = null;
        detailView.style.display = "none";
        defaultView.style.display = "block";
    }

    if (resetBtn) resetBtn.addEventListener("click", resetSidebar);

    function setupLayerEvents() {
        const mapEl = document.querySelector(".folium-map");
        if (!mapEl) return;
        const map = window[mapEl.id];
        if (!map) return setTimeout(setupLayerEvents, 150);

        map.eachLayer(function (layer) {
            if (layer instanceof L.GeoJSON) {
                window._mainGeoJsonLayer = layer;

                layer.eachLayer(function (featureLayer) {
                    featureLayer.on({
                        mouseover: function (e) {
                            if (lockedLayer) return;
                            currentHoverLayer = e.target;
                            currentHoverLayer.setStyle(HOVER_STYLE);
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
                            if (lockedLayer === e.target) {
                                layer.resetStyle(lockedLayer);
                                lockedLayer = null;
                                lockStatusBadge.textContent = "Hovering (Click to Lock)";
                                lockStatusBadge.classList.remove("locked");
                                resetSidebar();
                            } else {
                                if (lockedLayer) layer.resetStyle(lockedLayer);
                                lockedLayer = e.target;
                                lockedLayer.setStyle(LOCKED_STYLE);
                                lockedLayer.bringToFront();
                                lockStatusBadge.textContent = "Locked Selection";
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

    observer.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true
    });
});
