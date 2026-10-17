document.addEventListener("DOMContentLoaded", function () {
    const chartContainer = document.getElementById("gerrymander-chart");
    if (!chartContainer) return;

    const STATE_ELASTICITY = {
        "AL": 0.81, "MS": 0.79, "GA": 0.84, "SC": 0.88, "MD": 0.87,
        "LA": 0.93, "NC": 0.94, "VA": 0.92, "NY": 0.96, "CA": 0.96,
        "PA": 0.97, "IL": 0.98, "OH": 1.02, "TX": 1.02, "FL": 1.04,
        "MI": 1.03, "WI": 1.06, "AZ": 1.07, "NV": 1.08, "CO": 1.09,
        "IA": 1.13, "NH": 1.28, "ME": 1.17, "UT": 1.02
    };

    const STATE_MAP = {
        "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
        "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
        "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
        "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
        "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
        "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
        "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
        "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
        "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
        "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
        "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
        "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
        "WISCONSIN": "WI", "WYOMING": "WY"
    };

    function formatDistrictCode(rawCode, rawName) {
        if (typeof rawCode === "string" && rawCode.length === 4 && !rawCode.includes("-")) {
            return `${rawCode.slice(0, 2)}-${rawCode.slice(2)}`;
        }
        if (typeof rawCode === "string" && /^[A-Z]{2}-\d{1,2}$/i.test(rawCode)) {
            const parts = rawCode.split("-");
            return `${parts[0].toUpperCase()}-${parts[1].padStart(2, "0")}`;
        }
        if (typeof rawName === "string") {
            const clean = rawName.replace(/\*/g, "").trim();
            for (const [sName, sPostal] of Object.entries(STATE_MAP)) {
                if (clean.toUpperCase().startsWith(sName)) {
                    const match = clean.match(/(\d+)/);
                    if (match) {
                        return `${sPostal}-${match[1].padStart(2, "0")}`;
                    }
                }
            }
        }
        return rawCode || "UNK";
    }

    function parsePartisanIndex(str) {
        if (!str || str === "EVEN") return 0.0;
        const clean = String(str).replace(/\s+/g, "").toUpperCase();
        if (clean.startsWith("D+")) return parseFloat(clean.replace("D+", "")) || 0.0;
        if (clean.startsWith("R+")) return -parseFloat(clean.replace("R+", "")) || 0.0;
        const num = parseFloat(clean);
        return isNaN(num) ? 0.0 : num;
    }

    function isNonStandardRace(raceType) {
        if (!raceType) return false;
        const rt = String(raceType).toLowerCase();
        return !(rt.includes("standard") && !rt.includes("non-standard"));
    }

    function getScoreColor(val) {
        if (val >= 50) return "#10b981";
        if (val >= 0) return "#f59e0b";
        if (val >= -50) return "#f97316";
        return "#ef4444";
    }

    const candidatePaths = [
        "map2026.geojson",
        "docs/map2026.geojson",
        "../data/map2026.geojson"
    ];

    function loadGeoJSON(pathIndex) {
        if (pathIndex >= candidatePaths.length) {
            chartContainer.innerHTML = `
                <div style="padding: 24px; text-align: center; color: #ef4444; font-weight: 600;">
                    Unable to load map2026.geojson. Ensure you are running via a local web server.
                </div>
            `;
            return;
        }

        d3.json(candidatePaths[pathIndex]).then(function (geojson) {
            if (!geojson || !geojson.features) {
                loadGeoJSON(pathIndex + 1);
                return;
            }
            renderGerrymanderChart(geojson);
        }).catch(function () {
            loadGeoJSON(pathIndex + 1);
        });
    }

    loadGeoJSON(0);

    function renderGerrymanderChart(geojson) {
        const targetedFeatures = geojson.features.filter(f => {
            const t = f.properties && f.properties.Targeted;
            return t === true || t === "True" || t === 1;
        });

        if (targetedFeatures.length === 0) {
            chartContainer.innerHTML = `<p style="padding:24px;text-align:center;color:#64748b;">No districts flagged with Targeted=True.</p>`;
            return;
        }

        function calculateMetrics(feature) {
            const props = feature.properties || {};
            const id = formatDistrictCode(props.District, props.District_Name);
            const statePostal = id.slice(0, 2);

            const partisanIndex = parsePartisanIndex(props.Partisan_Lean_Index);
            const party = partisanIndex >= 0 ? "DEM" : "REP";

            const raceType = props.House_Race_Type || "Standard Contest";
            const nonStandard = isNonStandardRace(raceType);

            let base2024 = 0.0;
            if (nonStandard) {
                base2024 = (parseFloat(props["Margin 24"]) || 0.0) * 100;
            } else {
                const mov = (parseFloat(props.House_MOV_Raw) || 0.0) * 100;
                const winnerParty = String(props.House_Party || "").toUpperCase();
                base2024 = winnerParty.startsWith("D") ? mov : -mov;
            }

            const signedShift = partisanIndex - base2024;
            const absShift = Math.abs(signedShift);

            const sigma = 5.5;
            const beta_env = STATE_ELASTICITY[statePostal] || 0.85;
            const beta_inc = 2.5;

            const repParty = String(props.House_Party || "").toUpperCase();
            let incFactor = 0;
            if (repParty.startsWith("D")) incFactor = 1;
            else if (repParty.startsWith("R")) incFactor = -1;
            const incEffect = incFactor * beta_inc;

            // Scenario 1: 2026 Midterm (D+8.0 Environment)
            const env2026 = 8.0;
            const mu2026 = partisanIndex + (beta_env * env2026) + incEffect;
            const pDem2026 = 1 / (1 + Math.exp(-mu2026 / sigma));
            const pIntended2026 = party === "DEM" ? pDem2026 : (1 - pDem2026);
            const score2026 = 200 * (pIntended2026 - 0.50);

            // Scenario 2: Neutral Environment
            const muNeutral = partisanIndex + incEffect;
            const pDemNeutral = 1 / (1 + Math.exp(-muNeutral / sigma));
            const pIntendedNeutral = party === "DEM" ? pDemNeutral : (1 - pDemNeutral);
            const scoreNeutral = 200 * (pIntendedNeutral - 0.50);

            return {
                id,
                party,
                currentRep: props.Current_Rep || props.House_Winner || "N/A",
                repParty: props.House_Party || "OTHER",
                betaEnv: beta_env,
                partisanIndex: parseFloat(partisanIndex.toFixed(1)),
                signedShift: parseFloat(signedShift.toFixed(2)),
                absShift: parseFloat(absShift.toFixed(2)),
                score2026: parseFloat(score2026.toFixed(1)),
                scoreNeutral: parseFloat(scoreNeutral.toFixed(1)),
                p2026: (pIntended2026 * 100).toFixed(1),
                pNeutral: (pIntendedNeutral * 100).toFixed(1)
            };
        }

        const data = targetedFeatures.map(calculateMetrics);

        chartContainer.innerHTML = "";
        const margin = { top: 35, right: 35, bottom: 65, left: 65 };
        const width = 940 - margin.left - margin.right;
        const height = 490 - margin.top - margin.bottom;

        const svg = d3.select("#gerrymander-chart")
            .append("svg")
            .attr("viewBox", `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        const maxLean = d3.max(data, d => Math.abs(d.partisanIndex)) || 25;
        const xDomainLimit = Math.max(25, Math.ceil(maxLean / 5) * 5);

        const xScale = d3.scaleLinear().domain([-xDomainLimit, xDomainLimit]).range([0, width]);
        const yScale = d3.scaleLinear().domain([-100, 100]).range([height, 0]);

        const maxShiftVal = d3.max(data, d => d.absShift) || 40;
        const maxR = 24; 
        const rScale = d3.scaleSqrt().domain([0, maxShiftVal]).range([0, maxR]);

        // Gridlines
        svg.append("g")
            .attr("class", "chart-grid-line")
            .call(d3.axisLeft(yScale).ticks(8).tickSize(-width).tickFormat(""));

        // Center vertical divider (EVEN)
        svg.append("line")
            .attr("class", "chart-center-divider")
            .attr("x1", xScale(0)).attr("x2", xScale(0))
            .attr("y1", 0).attr("y2", height);

        // Zero horizontal baseline
        svg.append("line")
            .attr("class", "chart-zero-line")
            .attr("x1", 0).attr("x2", width)
            .attr("y1", yScale(0)).attr("y2", yScale(0));

        svg.append("text")
            .attr("class", "chart-threshold-label")
            .attr("x", width - 8)
            .attr("y", yScale(0) - 8)
            .text("50% Toss-Up / Break-Even Threshold");

        // X-Axis
        const xAxis = d3.axisBottom(xScale)
            .ticks(10)
            .tickFormat(d => d === 0 ? "EVEN" : (d < 0 ? `D+${Math.abs(d)}` : `R+${d}`));

        svg.append("g")
            .attr("class", "chart-axis")
            .attr("transform", `translate(0,${height})`)
            .call(xAxis);

        // Y-Axis
        svg.append("g")
            .attr("class", "chart-axis")
            .call(d3.axisLeft(yScale).ticks(8).tickFormat(d => d > 0 ? `+${d}` : d));

        svg.append("text")
            .attr("class", "chart-axis-label y-axis-title")
            .attr("transform", "rotate(-90)")
            .attr("x", -height / 2)
            .attr("y", -45)
            .text("Effectiveness Score* (100 = Successful Flip, -100 = Likely Fail)");

        // Axis Titles
        svg.append("text")
            .attr("class", "chart-axis-label dem-label")
            .attr("x", width / 4)
            .attr("y", height + 46)
            .text("← Dem-Favored Districts (Partisan Index)");

        svg.append("text")
            .attr("class", "chart-axis-label rep-label")
            .attr("x", (3 * width) / 4)
            .attr("y", height + 46)
            .text("GOP-Favored Districts (Partisan Index) →");

        // ---------------------------------------------------------------------
        // IN-CANVAS LEGEND BOX (Vertically Centered at Y = -90)
        // ---------------------------------------------------------------------
        const legCenterY = yScale(-90);
        const legBoxWidth = 275;
        const legBoxHeight = 32;

        const legendCard = svg.append("g")
            .attr("class", "chart-size-legend-card")
            .attr("transform", `translate(${xScale(-34)}, ${legCenterY - (legBoxHeight / 2)})`);

        legendCard.append("rect")
            .attr("width", legBoxWidth)
            .attr("height", legBoxHeight)
            .attr("rx", 6)
            .attr("fill", "#f8fafc")
            .attr("stroke", "#cbd5e1")
            .attr("stroke-width", 1.2);

        legendCard.append("circle")
            .attr("cx", 18)
            .attr("cy", legBoxHeight / 2)
            .attr("r", 8)
            .attr("fill", "#0f172a")
            .attr("fill-opacity", 0.08)
            .attr("stroke", "#0f172a")
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", "3, 2");

        legendCard.append("text")
            .attr("x", 34)
            .attr("y", (legBoxHeight / 2) + 4)
            .attr("font-size", "10.5px")
            .attr("font-weight", "800")
            .attr("fill", "#0f172a")
            .text("Size of Shift in Partisan Lean from 2024 to 2026");

        // ---------------------------------------------------------------------
        // BOTTOM RIGHT METHODOLOGY FOOTNOTE FOR ASTERISK
        // ---------------------------------------------------------------------
        svg.append("text")
            .attr("x", width - 4)
            .attr("y", yScale(-90) + 4)
            .attr("text-anchor", "end")
            .attr("font-size", "11px")
            .attr("font-weight", "600")
            .attr("fill", "#64748b")
            .text("* Explained in methodology section");

        const tooltip = d3.select("#chart-tooltip");

        function getActiveY(d, mode) {
            return mode === "neutral" ? d.scoreNeutral : d.score2026;
        }

        let currentMode = "2026";

        function computePositions(mode) {
            const items = data.map((d, index) => {
                const cx = xScale(d.party === "DEM" ? -Math.abs(d.partisanIndex) : Math.abs(d.partisanIndex));
                const cy = yScale(getActiveY(d, mode));
                const r = rScale(d.absShift);

                let initX = cx;
                let initY = cy;
                let anchor = "middle";

                if (cy < yScale(70)) {
                    initY = cy + r + 16;
                    initX = (index % 2 === 0) ? cx - 6 : cx + 6;
                    anchor = "middle";
                } else if (cy < yScale(30)) {
                    initX = cx + r + 18;
                    initY = (index % 2 === 0) ? cy - 8 : cy + 8;
                    anchor = "start";
                } else {
                    if (index % 2 === 0) {
                        initX = cx + r + 16;
                        initY = cy + 4;
                        anchor = "start";
                    } else {
                        initX = cx - r - 16;
                        initY = cy + 4;
                        anchor = "end";
                    }
                }

                return {
                    index,
                    d,
                    cx,
                    cy,
                    r,
                    x: initX,
                    y: initY,
                    anchor,
                    w: 48,
                    h: 16
                };
            });

            for (let iter = 0; iter < 10; iter++) {
                for (let i = 0; i < items.length; i++) {
                    const a = items[i];

                    for (let j = 0; j < items.length; j++) {
                        const circle = items[j];
                        const dCircle = Math.hypot(a.x - circle.cx, a.y - circle.cy);
                        const safeDist = circle.r + 14;
                        if (dCircle < safeDist) {
                            const angle = Math.atan2(a.y - circle.cy, a.x - circle.cx);
                            a.x = circle.cx + Math.cos(angle) * (safeDist + 2);
                            a.y = circle.cy + Math.sin(angle) * (safeDist + 2);
                        }
                    }

                    for (let j = i + 1; j < items.length; j++) {
                        const b = items[j];
                        const dx = a.x - b.x;
                        const dy = a.y - b.y;
                        if (Math.abs(dx) < 46 && Math.abs(dy) < 16) {
                            if (dy >= 0) { a.y += 8; b.y -= 8; }
                            else { a.y -= 8; b.y += 8; }
                        }
                    }
                }
            }

            items.forEach(item => {
                if (item.y < 16) item.y = 16;
                if (item.y > height - 12) item.y = height - 12;
                if (item.x < 38) { item.x = 38; item.anchor = "start"; }
                if (item.x > width - 38) { item.x = width - 38; item.anchor = "end"; }
            });

            return items;
        }

        let positions = computePositions(currentMode);

        const leaders = svg.selectAll(".label-leader-line")
            .data(positions, d => d.d.id)
            .enter()
            .append("line")
            .attr("class", d => `label-leader-line ${Math.hypot(d.x - d.cx, d.y - d.cy) > (d.r + 6) ? "active" : ""}`)
            .attr("stroke", "#334155")
            .attr("stroke-width", "1.5px")
            .attr("stroke-dasharray", "3, 2")
            .attr("opacity", d => Math.hypot(d.x - d.cx, d.y - d.cy) > (d.r + 6) ? 0.85 : 0)
            .attr("x1", d => d.cx)
            .attr("y1", d => d.cy)
            .attr("x2", d => d.x)
            .attr("y2", d => d.y);

        const nodes = svg.selectAll(".district-node")
            .data(positions, d => d.d.id)
            .enter()
            .append("g")
            .attr("class", "district-node")
            .on("mouseover", function (event, pos) {
                d3.select(this).raise();
                const d = pos.d;
                const score = getActiveY(d, currentMode);
                const scoreColor = getScoreColor(score);

                const pColorClass = d.party === "DEM" ? "dem-text" : "rep-text";
                const pIndexDisplay = d.partisanIndex > 0 ? `D+${d.partisanIndex}` : (d.partisanIndex < 0 ? `R+${Math.abs(d.partisanIndex)}` : "EVEN");
                
                const shiftColorClass = d.signedShift >= 0 ? "dem-text" : "rep-text";
                const shiftDisplay = d.signedShift >= 0 ? `D +${d.signedShift.toFixed(2)}%` : `R +${Math.abs(d.signedShift).toFixed(2)}%`;

                const repPartyClass = String(d.repParty).toUpperCase().startsWith("D") ? "dem-text" : (String(d.repParty).toUpperCase().startsWith("R") ? "rep-text" : "");

                tooltip.classed("visible", true)
                    .html(`
                        <div class="tt-title">${d.id} (${d.party})</div>
                        <div class="tt-row">
                            <span>Representative*:</span>
                            <strong class="${repPartyClass}">${d.currentRep}</strong>
                        </div>
                        <div class="tt-row">
                            <span>Partisan Index*:</span>
                            <strong class="${pColorClass}">${pIndexDisplay}</strong>
                        </div>
                        <div class="tt-row">
                            <span>Partisan Shift*:</span>
                            <strong class="${shiftColorClass}">${shiftDisplay}</strong>
                        </div>
                        <div class="tt-row">
                            <span>State Elasticity*:</span>
                            <strong>${d.betaEnv.toFixed(2)}</strong>
                        </div>
                        <div class="tt-row">
                            <span>2026 Flip Prob:</span>
                            <strong>${d.p2026}%</strong>
                        </div>
                        <div class="tt-row">
                            <span>Neutral Flip Prob:</span>
                            <strong>${d.pNeutral}%</strong>
                        </div>
                        <div class="tt-divider"></div>
                        <div class="tt-row">
                            <span>Effectiveness Score*:</span>
                            <strong style="color: ${scoreColor} !important; font-size: 1.05rem; font-weight: 900;">
                                ${score > 0 ? "+" + score : score}
                            </strong>
                        </div>
                    `);

                // 100% Reliable SVG-to-Container Pixel Mapping (No Viewport Glitches)
                const containerNode = document.getElementById("gerrymander-chart");
                const cRect = containerNode.getBoundingClientRect();

                const tWidth = 220;
                const tHeight = 270;

                // Map SVG internal units to actual rendered container dimensions
                const svgBox = svg.node().getBoundingClientRect();
                const scaleX = svgBox.width / (width + margin.left + margin.right);
                const scaleY = svgBox.height / (height + margin.top + margin.bottom);

                const renderX = (pos.cx + margin.left) * scaleX + (svgBox.left - cRect.left);
                const renderY = (pos.cy + margin.top) * scaleY + (svgBox.top - cRect.top);

                let posX, posY;

                // Smart Horizontal Placement: If bubble is on right half, put tooltip to the left
                if (pos.cx > width / 2) {
                    posX = renderX - tWidth - 14;
                } else {
                    posX = renderX + 18;
                }

                // Vertical Clamping: Keep box strictly inside the card container boundaries
                posY = renderY - (tHeight / 2);
                const maxPosY = cRect.height - tHeight - 12;
                posY = Math.max(12, Math.min(posY, maxPosY));

                tooltip.style("left", posX + "px")
                       .style("top", posY + "px")
                       .style("transform", "none");
            })
            .on("mousemove", function (event) {
                // Static per-hover lock prevents jump bugs
            })
            .on("mouseout", function () {
                tooltip.classed("visible", false);
            });

        nodes.append("circle")
            .attr("class", d => `district-dot ${d.d.party.toLowerCase()}`)
            .attr("cx", d => d.cx)
            .attr("cy", d => d.cy)
            .attr("r", d => d.r);

        nodes.append("text")
            .attr("class", "chart-dot-label")
            .attr("x", d => d.x)
            .attr("y", d => d.y)
            .attr("text-anchor", d => d.anchor)
            .text(d => d.d.id);

        document.querySelectorAll(".scenario-btn").forEach(btn => {
            btn.addEventListener("click", function () {
                document.querySelectorAll(".scenario-btn").forEach(b => b.classList.remove("active"));
                this.classList.add("active");
                currentMode = this.getAttribute("data-mode");

                positions = computePositions(currentMode);

                nodes.data(positions, d => d.d.id)
                    .each(function(d) {
                        const g = d3.select(this);
                        g.select("circle")
                            .transition()
                            .duration(650)
                            .ease(d3.easeCubicInOut)
                            .attr("cy", d.cy);

                        g.select("text")
                            .transition()
                            .duration(650)
                            .ease(d3.easeCubicInOut)
                            .attr("x", d.x)
                            .attr("y", d.y)
                            .attr("text-anchor", d.anchor);
                    });

                leaders.data(positions, d => d.d.id)
                    .attr("opacity", d => Math.hypot(d.x - d.cx, d.y - d.cy) > (d.r + 6) ? 0.85 : 0)
                    .transition()
                    .duration(650)
                    .ease(d3.easeCubicInOut)
                    .attr("x1", d => d.cx)
                    .attr("y1", d => d.cy)
                    .attr("x2", d => d.x)
                    .attr("y2", d => d.y);
            });
        });
    }
});
