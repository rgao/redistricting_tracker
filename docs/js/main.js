document.addEventListener("DOMContentLoaded", function () {

    // 1. Navigation Management
    (function manageNavigation() {
        const navContainer = document.querySelector(".map-page-navigation");
        if (!navContainer) return;

        const currentPath = window.location.pathname.split("/").pop();
        let activePage = "index.html";
        if (currentPath === "shift.html") activePage = "shift.html";
        else if (currentPath === "analysis.html") activePage = "analysis.html";

        navContainer.setAttribute("data-current-page", activePage);
        const targetLink = navContainer.querySelector(`a[href="${activePage}"]`);
        if (targetLink) {
            navContainer.querySelectorAll(".nav-btn").forEach(btn => btn.classList.remove("active"));
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

    // Hover: Gold
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

    function formatSignedMargin(val) {
        if (val === null || val === undefined || isNaN(val)) return 'EVEN';
        const pct = Math.abs(val) * 100;
        if (pct < 0.005) return 'EVEN';
        return (val > 0 ? 'Harris +' : 'Trump +') + pct.toFixed(2) + '%';
    }

    function formatShiftMargin(val) {
        if (val === null || val === undefined || isNaN(val)) return 'EVEN';
        const pct = Math.abs(val) * 100;
        if (pct < 0.005) return 'EVEN';
        return (val > 0 ? 'Harris +' : 'Trump +') + pct.toFixed(2) + '%';
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

        // 1. Sidebar District Header & Status Caption
        document.getElementById("sb-detail-district-title").textContent = props.District_Name || props.District;
        const statusEl = document.getElementById("sb-detail-status");
        if (props.Targeted) {
            statusEl.textContent = "Redrawn District";
            statusEl.style.display = "block";
        } else {
            statusEl.textContent = "";
            statusEl.style.display = "none";
        }

        // Partisan Lean Index
        const blnEl = document.getElementById("sb-detail-blended-lean");
        const partisanLeanText = props.Partisan_Lean_Index || "EVEN";
        blnEl.textContent = partisanLeanText;
        applyPartyColor(blnEl, partisanLeanText.startsWith("D") ? "DEM" : partisanLeanText.startsWith("R") ? "REP" : null);

        // Presidential Vote Share Rows (2024 Boundaries, 2026 Boundaries, Shift)
        const m24 = parseFloat(props["Margin 24"]);
        const mNew = parseFloat(props["Margin New"]);
        const mShift = parseFloat(props["Margin Shift"]);

        const p24Elem = document.getElementById("sb-detail-pres-24");
        p24Elem.textContent = formatSignedMargin(m24);
        p24Elem.className = "pres-row-val " + (m24 > 0.00005 ? "dem" : (m24 < -0.00005 ? "rep" : ""));

        const pNewElem = document.getElementById("sb-detail-pres-new");
        pNewElem.textContent = formatSignedMargin(mNew);
        pNewElem.className = "pres-row-val " + (mNew > 0.00005 ? "dem" : (mNew < -0.00005 ? "rep" : ""));

        const pShiftElem = document.getElementById("sb-detail-pres-shift");
        pShiftElem.textContent = formatShiftMargin(mShift);
        pShiftElem.className = "pres-row-val " + (mShift > 0.00005 ? "dem" : (mShift < -0.00005 ? "rep" : ""));

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

        // 4. Demographics (VAP) formatted to 1 decimal place
        document.getElementById("sb-detail-white-pct").textContent = ((props.WhitePct || 0) * 100).toFixed(1) + "%";
        document.getElementById("sb-detail-hispanic-pct").textContent = ((props.HispanicPct || 0) * 100).toFixed(1) + "%";
        document.getElementById("sb-detail-black-pct").textContent = ((props.BlackPct || 0) * 100).toFixed(1) + "%";
        document.getElementById("sb-detail-asian-pct").textContent = ((props.AsianPct || 0) * 100).toFixed(1) + "%";
        document.getElementById("sb-detail-minority-pct").textContent = ((props.MinorityPct || 0) * 100).toFixed(1) + "%";
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

        const statusEl = document.getElementById("sb-detail-status");
        if (statusEl) {
            statusEl.textContent = "";
            statusEl.style.display = "none";
        }

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

// Interactive Click-to-Open Info Tooltips
document.addEventListener('click', function (e) {
    const infoBtn = e.target.closest('.info-tooltip-icon');
    const closeBtn = e.target.closest('.popover-close');
    const existingPopover = document.querySelector('.metric-info-popover');

    // 1. Close button clicked
    if (closeBtn && existingPopover) {
        e.preventDefault();
        e.stopPropagation();
        existingPopover.remove();
        return;
    }

    // 2. Info icon clicked
    if (infoBtn) {
        e.preventDefault();
        e.stopPropagation();

        if (existingPopover) {
            existingPopover.remove();
        }

        const infoText = infoBtn.getAttribute('data-info');
        if (!infoText) return;

        const popover = document.createElement('div');
        popover.className = 'metric-info-popover';
        popover.innerHTML = `<button type="button" class="popover-close" aria-label="Close">✕</button>${infoText}`;

        document.body.appendChild(popover);

        const rect = infoBtn.getBoundingClientRect();
        popover.style.top = (rect.bottom + window.scrollY + 6) + 'px';
        popover.style.left = Math.min(rect.left + window.scrollX, window.innerWidth - 280) + 'px';
        return;
    }

    // 3. Click outside popover closes it
    if (existingPopover && !e.target.closest('.metric-info-popover')) {
        existingPopover.remove();
    }

    // Toggle State: '2026', 'neutral', or 'blended'
    let currentMode = '2026';

    function updateChart(mode) {
        currentMode = mode;

        // Select target value based on the active mode
        svg.selectAll(".district-dot")
            .transition()
            .duration(650)
            .ease(d3.easeCubicInOut)
            .attr("cy", d => {
                let score;
                if (mode === '2026') score = 200 * ((d.p2026 / 100) - 0.50);
                else if (mode === 'neutral') score = 200 * ((d.p2028 / 100) - 0.50);
                else score = parseFloat(d.ges); // Blended
                return yScale(score);
            });

        svg.selectAll(".dot-label")
            .transition()
            .duration(650)
            .ease(d3.easeCubicInOut)
            .attr("y", d => {
                let score;
                if (mode === '2026') score = 200 * ((d.p2026 / 100) - 0.50);
                else if (mode === 'neutral') score = 200 * ((d.p2028 / 100) - 0.50);
                else score = parseFloat(d.ges);
                return yScale(score) - rScale(parseFloat(d.shift)) - 4;
            });
    }
});
