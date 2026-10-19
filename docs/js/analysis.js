document.addEventListener("DOMContentLoaded", function () {

    // =========================================================================
    // 1. INDIVIDUAL DISTRICT GERRYMANDER DURABILITY CHART (CHART 1)
    // =========================================================================
    const chartContainer = document.getElementById("gerrymander-chart");
    if (chartContainer) {
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
                        if (match) return `${sPostal}-${match[1].padStart(2, "0")}`;
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
            "../docs/map2026.geojson",
            "../data/map2026.geojson"
        ];

        function loadGeoJSON(pathIndex) {
            if (pathIndex >= candidatePaths.length) {
                chartContainer.innerHTML = `<div style="padding:24px;text-align:center;color:#ef4444;font-weight:600;">Unable to load map2026.geojson. Make sure a local web server is running.</div>`;
                return;
            }

            d3.json(candidatePaths[pathIndex]).then(function (geojson) {
                if (!geojson || !geojson.features) {
                    loadGeoJSON(pathIndex + 1);
                    return;
                }
                renderGerrymanderChart(geojson);
                renderStateChart();
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

                const sigma = 3.9;
                const beta_env = STATE_ELASTICITY[statePostal] || 0.95;

                const env2026 = 8.0;
                const mu2026 = partisanIndex + (beta_env * env2026);
                const pDem2026 = 1 / (1 + Math.exp(-mu2026 / sigma));
                const pIntended2026 = party === "DEM" ? pDem2026 : (1 - pDem2026);
                const score2026 = 200 * (pIntended2026 - 0.50);

                const muNeutral = partisanIndex;
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
            const margin = { top: 60, right: 65, bottom: 65, left: 65 };
            const width = 960 - margin.left - margin.right;
            const height = 520 - margin.top - margin.bottom;

            const svg = d3.select("#gerrymander-chart")
                .append("svg")
                .attr("viewBox", `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
                .append("g")
                .attr("transform", `translate(${margin.left},${margin.top})`);

            const maxLean = d3.max(data, d => Math.abs(d.partisanIndex)) || 25;
            const xDomainLimit = Math.max(30, Math.ceil(maxLean / 5) * 5);

            const xScale = d3.scaleLinear().domain([-xDomainLimit, xDomainLimit]).range([0, width]);
            const yScale = d3.scaleLinear().domain([-100, 100]).range([height, 0]);

            const maxShiftVal = d3.max(data, d => d.absShift) || 40;
            const maxR = 24;
            const rScale = d3.scaleSqrt().domain([0, maxShiftVal]).range([0, maxR]);

            svg.append("g").attr("class", "chart-grid-line").call(d3.axisLeft(yScale).ticks(8).tickSize(-width).tickFormat(""));
            svg.append("line").attr("class", "chart-center-divider").attr("x1", xScale(0)).attr("x2", xScale(0)).attr("y1", 0).attr("y2", height);
            svg.append("line").attr("class", "chart-zero-line").attr("x1", 0).attr("x2", width).attr("y1", yScale(0)).attr("y2", yScale(0));

            svg.append("text").attr("class", "chart-threshold-label").attr("x", width - 8).attr("y", yScale(0) - 8).text("50% Toss-Up / Break-Even Threshold");

            const xAxis = d3.axisBottom(xScale).ticks(12).tickFormat(d => d === 0 ? "EVEN" : (d < 0 ? `D+${Math.abs(d)}` : `R+${d}`));
            svg.append("g").attr("class", "chart-axis").attr("transform", `translate(0,${height})`).call(xAxis);
            svg.append("g").attr("class", "chart-axis").call(d3.axisLeft(yScale).ticks(8).tickFormat(d => d > 0 ? `+${d}` : d));

            svg.append("text").attr("class", "chart-axis-label y-axis-title").attr("transform", "rotate(-90)").attr("x", -height / 2).attr("y", -45).text("Effectiveness Score* (100 = Successful Flip, -100 = Likely Fail)");
            svg.append("text").attr("class", "chart-axis-label dem-label").attr("x", width / 4).attr("y", height + 46).text("← Dem-Favored Districts (Partisan Index)");
            svg.append("text").attr("class", "chart-axis-label rep-label").attr("x", (3 * width) / 4).attr("y", height + 46).text("GOP-Favored Districts (Partisan Index) →");

            const legCenterY = yScale(-90);
            const legBoxWidth = 275;
            const legBoxHeight = 32;

            const legendCard = svg.append("g").attr("class", "chart-size-legend-card").attr("transform", `translate(${xScale(-32)}, ${legCenterY - (legBoxHeight / 2)})`);
            legendCard.append("rect").attr("width", legBoxWidth).attr("height", legBoxHeight).attr("rx", 6).attr("fill", "#f8fafc").attr("stroke", "#cbd5e1").attr("stroke-width", 1.2);
            legendCard.append("circle").attr("cx", 18).attr("cy", legBoxHeight / 2).attr("r", 8).attr("fill", "#0f172a").attr("fill-opacity", 0.08).attr("stroke", "#0f172a").attr("stroke-width", 2).attr("stroke-dasharray", "3, 2");
            legendCard.append("text").attr("x", 34).attr("y", (legBoxHeight / 2) + 4).attr("font-size", "10.5px").attr("font-weight", "800").attr("fill", "#0f172a").text("Size of Shift in Partisan Lean from 2024 to 2026");

            svg.append("text").attr("x", width - 4).attr("y", yScale(-90) + 4).attr("text-anchor", "end").attr("font-size", "11px").attr("font-weight", "600").attr("fill", "#64748b").text("* Explained in methodology section");

            const tooltip = d3.select("#chart-tooltip");
            function getActiveY(d, mode) { return mode === "neutral" ? d.scoreNeutral : d.score2026; }
            let currentMode = "2026";

            function computePositions(mode) {
                const nodes = data.map(d => {
                    const cx = xScale(d.party === "DEM" ? -Math.abs(d.partisanIndex) : Math.abs(d.partisanIndex));
                    const cy = yScale(getActiveY(d, mode));
                    const r = rScale(d.absShift);
                    return { d, cx, cy, r };
                });

                // Sort left-to-right for consistent processing order
                nodes.sort((a, b) => a.cx - b.cx);

                const labelW = 56;
                const labelH = 16;
                const placedLabels = [];

                // Strict box-to-circle collision check
                function boxCollidesWithCircles(x, y) {
                    const l = x - labelW / 2 - 4;
                    const r_box = x + labelW / 2 + 4;
                    const t = y - labelH / 2 - 4;
                    const b = y + labelH / 2 + 4;

                    for (let node of nodes) {
                        const closestX = Math.max(l, Math.min(node.cx, r_box));
                        const closestY = Math.max(t, Math.min(node.cy, b));
                        const distX = node.cx - closestX;
                        const distY = node.cy - closestY;
                        if ((distX * distX + distY * distY) < (node.r + 6) ** 2) {
                            return true;
                        }
                    }
                    return false;
                }

                // Strict rectangular bounding box (AABB) intersection check for text labels
                function boxCollidesWithLabels(x, y) {
                    const l1 = x - labelW / 2;
                    const r1 = x + labelW / 2;
                    const t1 = y - labelH / 2;
                    const b1 = y + labelH / 2;

                    for (let p of placedLabels) {
                        const l2 = p.x - labelW / 2;
                        const r2 = p.x + labelW / 2;
                        const t2 = p.y - labelH / 2;
                        const b2 = p.y + labelH / 2;

                        // Check for overlap with padding buffer
                        if (l1 < r2 + 6 && r1 > l2 - 6 && t1 < b2 + 4 && b1 > t2 - 4) {
                            return true;
                        }
                    }
                    return false;
                }

                return nodes.map(node => {
                    const cx = node.cx;
                    const cy = node.cy;
                    const r = node.r;

                    let bestY = cy - r - 18;
                    let found = false;

                    // Fine-grained vertical steps covering the entire Y-axis space as needed
                    const verticalSteps = [
                        18, 24, 30, 36, 42, 48, 54, 62, 70, 80, 90, 102, 114, 128, 144, 162, 182, 204
                    ];

                    // 1. Try strictly above first, stretching upward
                    for (let offset of verticalSteps) {
                        let ty = cy - r - offset;
                        if (ty >= 20 && !boxCollidesWithCircles(cx, ty) && !boxCollidesWithLabels(cx, ty)) {
                            bestY = ty;
                            found = true;
                            break;
                        }
                    }

                    // 2. If above is blocked, try strictly beneath, stretching downward
                    if (!found) {
                        for (let offset of verticalSteps) {
                            let ty = cy + r + offset;
                            if (ty <= height - 16 && !boxCollidesWithCircles(cx, ty) && !boxCollidesWithLabels(cx, ty)) {
                                bestY = ty;
                                found = true;
                                break;
                            }
                        }
                    }

                    // Ultimate fallback
                    if (!found) {
                        bestY = Math.max(20, Math.min(height - 16, cy - r - 220));
                    }

                    const placed = { d: node.d, cx, cy, r, x: cx, y: bestY, anchor: "middle" };
                    placedLabels.push(placed);
                    return placed;
                });
            }

            let positions = computePositions(currentMode);

            const leaders = svg.selectAll(".label-leader-line")
                .data(positions, d => d.d.id)
                .enter()
                .append("line")
                .attr("class", d => `label-leader-line ${Math.hypot(d.x - d.cx, d.y - d.cy) > (d.r + 6) ? "active" : ""}`)
                .attr("stroke", "#334155").attr("stroke-width", "1.5px").attr("stroke-dasharray", "3, 2")
                .attr("opacity", d => Math.hypot(d.x - d.cx, d.y - d.cy) > (d.r + 6) ? 0.85 : 0)
                .attr("x1", d => d.cx).attr("y1", d => d.cy).attr("x2", d => d.x).attr("y2", d => d.y);

            const nodes = svg.selectAll(".district-node")
                .data(positions, d => d.d.id)
                .enter()
                .append("g")
                .attr("class", "district-node")
                .style("pointer-events", "all")
                .style("cursor", "pointer")
                .on("mouseover", function (event, pos) {
                    d3.select(this).raise();
                    const d = pos.d;
                    const score = getActiveY(d, currentMode);
                    const scoreColor = getScoreColor(score);
                    const pColorClass = d.party === "DEM" ? "dem-text" : "rep-text";
                    const pIndexDisplay = d.partisanIndex > 0 ? `D+${d.partisanIndex}` : (d.partisanIndex < 0 ? `R+${Math.abs(d.partisanIndex)}` : "EVEN");
                    const shiftColorClass = d.signedShift >= 0 ? "dem-text" : "rep-text";
                    // 1-decimal formatting
                    const shiftDisplay = d.signedShift >= 0 ? `D +${d.signedShift.toFixed(1)}%` : `R +${Math.abs(d.signedShift).toFixed(1)}%`;
                    const repPartyClass = String(d.repParty).toUpperCase().startsWith("D") ? "dem-text" : (String(d.repParty).toUpperCase().startsWith("R") ? "rep-text" : "");

                    tooltip.classed("visible", true)
                        .html(`
                            <div class="tt-title">${d.id} (${d.party})</div>
                            <div class="tt-row"><span>Representative*:</span> <strong class="${repPartyClass}">${d.currentRep}</strong></div>
                            <div class="tt-row"><span>Partisan Index*:</span> <strong class="${pColorClass}">${pIndexDisplay}</strong></div>
                            <div class="tt-row"><span>Partisan Shift*:</span> <strong class="${shiftColorClass}">${shiftDisplay}</strong></div>
                            <div class="tt-row"><span>State Elasticity*:</span> <strong>${d.betaEnv.toFixed(2)}</strong></div>
                            <div class="tt-row"><span>2026 Flip Prob:</span> <strong>${d.p2026}%</strong></div>
                            <div class="tt-row"><span>Neutral Flip Prob:</span> <strong>${d.pNeutral}%</strong></div>
                            <div class="tt-divider"></div>
                            <div class="tt-row"><span>Effectiveness Score*:</span> <strong style="color: ${scoreColor} !important; font-size: 1.05rem; font-weight: 900;">${score > 0 ? "+" + score : score}</strong></div>
                        `);

                    const containerNode = document.getElementById("gerrymander-chart");
                    const cRect = containerNode.getBoundingClientRect();
                    const tWidth = 220; const tHeight = 270;
                    const svgBox = svg.node().getBoundingClientRect();
                    const scaleX = svgBox.width / (width + margin.left + margin.right);
                    const scaleY = svgBox.height / (height + margin.top + margin.bottom);
                    const renderX = (pos.cx + margin.left) * scaleX + (svgBox.left - cRect.left);
                    const renderY = (pos.cy + margin.top) * scaleY + (svgBox.top - cRect.top);

                    let posX = pos.cx > width / 2 ? renderX - tWidth - 14 : renderX + 18;
                    let posY = Math.max(12, Math.min(renderY - (tHeight / 2), cRect.height - tHeight - 12));

                    tooltip.style("left", posX + "px").style("top", posY + "px").style("transform", "none");
                })
                .on("mouseout", function () { tooltip.classed("visible", false); });

            nodes.append("circle")
                .attr("class", d => `district-dot ${d.d.party.toLowerCase()}`)
                .attr("cx", d => d.cx).attr("cy", d => d.cy).attr("r", d => d.r);

            nodes.append("text")
                .attr("class", "chart-dot-label")
                .attr("x", d => d.x).attr("y", d => d.y).attr("text-anchor", d => d.anchor)
                .style("pointer-events", "all")
                .style("cursor", "pointer")
                .text(d => d.d.id);

            window.updateGerrymanderChart = function (newMode) {
                currentMode = newMode;
                positions = computePositions(currentMode);

                nodes.data(positions, d => d.d.id).each(function (d) {
                    const g = d3.select(this);
                    g.select("circle").transition().duration(650).ease(d3.easeCubicInOut).attr("cy", d.cy);
                    g.select("text").transition().duration(650).ease(d3.easeCubicInOut).attr("x", d.x).attr("y", d.y).attr("text-anchor", d.anchor);
                });

                leaders.data(positions, d => d.d.id)
                    .attr("opacity", d => Math.hypot(d.x - d.cx, d.y - d.cy) > (d.r + 6) ? 0.85 : 0)
                    .transition().duration(650).ease(d3.easeCubicInOut)
                    .attr("x1", d => d.cx).attr("y1", d => d.cy).attr("x2", d => d.x).attr("y2", d => d.y);
            };
        }
    }

    // =========================================================================
    // 2. STATE-LEVEL DELEGATION CHANGES (CHART 2)
    // =========================================================================
    function renderStateChart() {
        const stateChartContainer = document.getElementById("state-delegation-chart");
        if (!stateChartContainer) return;

        const stateDelegationData = [
            { state: "California", abbr: "CA", party: "DEM", targeted: 5, ev2026: 4.75, evNeutral: 4.15, preDem: 43, preRep: 9, totalSeats: 52, targetDem: 48, targetRep: 4 },
            { state: "Texas", abbr: "TX", party: "REP", targeted: 5, ev2026: 3.10, evNeutral: 3.87, preDem: 13, preRep: 25, totalSeats: 38, targetDem: 8, targetRep: 30 },
            { state: "Florida", abbr: "FL", party: "REP", targeted: 4, ev2026: 2.85, evNeutral: 3.60, preDem: 8, preRep: 20, totalSeats: 28, targetDem: 4, targetRep: 24 },
            { state: "Ohio", abbr: "OH", party: "REP", targeted: 2, ev2026: 1.25, evNeutral: 1.75, preDem: 5, preRep: 10, totalSeats: 15, targetDem: 3, targetRep: 12 },
            { state: "North Carolina", abbr: "NC", party: "REP", targeted: 1, ev2026: 0.30, evNeutral: 0.42, preDem: 4, preRep: 10, totalSeats: 14, targetDem: 3, targetRep: 11 },
            { state: "Tennessee", abbr: "TN", party: "REP", targeted: 1, ev2026: 0.95, evNeutral: 0.98, preDem: 1, preRep: 8, totalSeats: 9, targetDem: 0, targetRep: 9 },
            { state: "Alabama", abbr: "AL", party: "REP", targeted: 1, ev2026: 0.88, evNeutral: 0.95, preDem: 2, preRep: 5, totalSeats: 7, targetDem: 1, targetRep: 6 },
            { state: "Louisiana", abbr: "LA", party: "REP", targeted: 1, ev2026: 0.85, evNeutral: 0.92, preDem: 2, preRep: 4, totalSeats: 6, targetDem: 1, targetRep: 5 }
        ];

        stateChartContainer.innerHTML = "";
        const margin = { top: 45, right: 65, bottom: 65, left: 65 };
        const width = 940 - margin.left - margin.right;
        const height = 460 - margin.top - margin.bottom;

        const svg = d3.select("#state-delegation-chart")
            .append("svg")
            .attr("viewBox", `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        const xScale = d3.scaleLinear().domain([-6, 6]).range([0, width]);
        // Negative Y-axis ending at -0.5 (half-row buffer)[cite: 18, 23]
        const yScale = d3.scaleLinear().domain([-0.5, 5.5]).range([height, 0]);

        svg.append("g").attr("class", "chart-grid-line").call(d3.axisLeft(yScale).ticks(7).tickSize(-width).tickFormat(""));
        svg.append("line").attr("class", "chart-center-divider").attr("x1", xScale(0)).attr("x2", xScale(0)).attr("y1", 0).attr("y2", height);
        svg.append("line").attr("class", "chart-zero-line").attr("x1", 0).attr("x2", width).attr("y1", yScale(0)).attr("y2", yScale(0));

        svg.append("g").attr("class", "chart-axis").attr("transform", `translate(0,${height})`).call(d3.axisBottom(xScale).ticks(12).tickFormat(d => Math.abs(d)));
        svg.append("g").attr("class", "chart-axis").call(d3.axisLeft(yScale).ticks(7).tickFormat(d => d > 0 ? `+${d.toFixed(1)}` : d.toFixed(1)));

        svg.append("text")
            .attr("class", "chart-axis-label")
            .attr("x", width / 2)
            .attr("y", height + 46)
            .attr("text-anchor", "middle")
            .attr("fill", "#0f172a")
            .attr("font-size", "12px")
            .attr("font-weight", "700")
            .text("Number of Targeted Seats");

        svg.append("text")
            .attr("class", "chart-axis-label dem-label")
            .attr("x", width / 6)
            .attr("y", height + 46)
            .attr("text-anchor", "middle")
            .text("← Dem Targets");

        svg.append("text")
            .attr("class", "chart-axis-label rep-label")
            .attr("x", (5 * width) / 6)
            .attr("y", height + 46)
            .attr("text-anchor", "middle")
            .text("GOP Targets →");

        svg.append("text")
            .attr("class", "chart-axis-label y-axis-title")
            .attr("transform", "rotate(-90)")
            .attr("x", -height / 2)
            .attr("y", -45)
            .text("Expected Value of Net Seat Change");

        const tooltip = d3.select("#state-tooltip");
        let currentStateMode = "2026";

        function getEV(d, mode) { return mode === "neutral" ? d.evNeutral : d.ev2026; }

        // Clean vertical fanning for the cluster of states sharing x = 1[cite: 31]
        function getPositions(mode) {
            return stateDelegationData.map(d => {
                const cx = xScale(d.party === "DEM" ? -d.targeted : d.targeted);
                const cy = yScale(getEV(d, mode));
                const r = 16;
                let lx = cx, ly = cy, anchor = "middle";

                if (d.abbr === "CA") {
                    lx = cx; ly = cy - r - 8; anchor = "middle";
                } else if (d.abbr === "TX") {
                    lx = cx; ly = cy - r - 8; anchor = "middle";
                } else if (d.abbr === "FL") {
                    lx = cx; ly = cy + r + 14; anchor = "middle";
                } else if (d.abbr === "OH") {
                    lx = cx + r + 14; ly = cy + 4; anchor = "start";
                } else if (d.abbr === "TN") {
                    // Top in stack: up-left diagonal
                    lx = cx - 42; ly = cy - 26; anchor = "end";
                } else if (d.abbr === "LA") {
                    // Middle in stack: directly horizontal to the left
                    lx = cx - 42; ly = cy - 2; anchor = "end";
                } else if (d.abbr === "AL") {
                    // Bottom in stack: down-left diagonal
                    lx = cx - 42; ly = cy + 22; anchor = "end";
                } else if (d.abbr === "NC") {
                    // North Carolina sits cleanly on the right
                    lx = cx + 38; ly = cy + 4; anchor = "start";
                }

                return { d, cx, cy, r, lx, ly, anchor };
            });
        }

        let positions = getPositions(currentStateMode);

        const stateNodes = svg.selectAll(".state-scatter-node")
            .data(positions, d => d.d.abbr).enter().append("g")
            .attr("class", "state-scatter-node")
            .style("pointer-events", "all")
            .style("cursor", "pointer")
            .on("mouseover", function (event, pos) {
                d3.select(this).raise();
                const d = pos.d;
                const currentEV = getEV(d, currentStateMode);
                const intGain = Math.round(currentEV);

                let outcomeColor = "#10b981";
                if (intGain >= d.targeted) {
                    outcomeColor = "#10b981";
                } else if (intGain > 0) {
                    outcomeColor = "#f59e0b";
                } else {
                    outcomeColor = "#ef4444";
                }

                const netChangeDisplay = intGain > 0 ? `+${intGain}` : `${intGain}`;
                const evDisplay = currentEV > 0 ? `+${currentEV.toFixed(2)}` : `${currentEV.toFixed(2)}`;

                const preDemStr = `<span style="color: #60a5fa !important; font-weight: 800;">${d.preDem}D</span>`;
                const preRepStr = `<span style="color: #f87171 !important; font-weight: 800;">${d.preRep}R</span>`;
                const targetDemStr = `<span style="color: #60a5fa !important; font-weight: 800;">${d.targetDem}D</span>`;
                const targetRepStr = `<span style="color: #f87171 !important; font-weight: 800;">${d.targetRep}R</span>`;

                tooltip.classed("visible", true)
                    .html(`
                        <div class="tt-title">State: ${d.state} (${d.party})</div>
                        <div class="tt-row"><span>Targeted Seats:</span> <strong>${d.targeted}</strong></div>
                        <div class="tt-row"><span>Expected Net Seat Change:</span> <strong style="color: ${outcomeColor} !important;">${netChangeDisplay}</strong></div>
                        <div class="tt-row"><span>Expected Value:</span> <strong style="color: ${outcomeColor} !important;">${evDisplay}</strong></div>
                        <div class="tt-divider"></div>
                        <div class="tt-row"><span>2024 Map Delegation:</span> <strong>${preDemStr} - ${preRepStr}</strong></div>
                        <div class="tt-row"><span>Target Delegation:</span> <strong>${targetDemStr} - ${targetRepStr}</strong></div>
                    `);

                const containerNode = document.getElementById("state-delegation-chart");
                const cRect = containerNode.getBoundingClientRect();
                const tWidth = 240; const tHeight = 220;
                const svgBox = svg.node().getBoundingClientRect();
                const renderX = (pos.cx + margin.left) * (svgBox.width / (width + margin.left + margin.right)) + (svgBox.left - cRect.left);
                const renderY = (pos.cy + margin.top) * (svgBox.height / (height + margin.top + margin.bottom)) + (svgBox.top - cRect.top);

                let posX = pos.cx > width / 2 ? renderX - tWidth - 14 : renderX + 18;
                let posY = Math.max(12, Math.min(renderY - (tHeight / 2), cRect.height - tHeight - 12));

                tooltip.style("left", posX + "px").style("top", posY + "px").style("transform", "none");
            })
            .on("mouseout", function () { tooltip.classed("visible", false); });

        stateNodes.append("line")
            .attr("class", "leader-hover-buffer")
            .attr("stroke", "transparent")
            .attr("stroke-width", "16px")
            .attr("x1", d => d.cx).attr("y1", d => d.cy).attr("x2", d => d.lx).attr("y2", d => d.ly);

        stateNodes.append("line")
            .attr("class", "state-leader-line")
            .attr("stroke", "#64748b").attr("stroke-width", "1.2px").attr("stroke-dasharray", "3, 2")
            .attr("opacity", d => Math.hypot(d.lx - d.cx, d.ly - d.cy) > (d.r + 14) ? 0.85 : 0)
            .attr("x1", d => d.cx).attr("y1", d => d.cy).attr("x2", d => d.lx).attr("y2", d => d.ly);

        stateNodes.append("circle")
            .attr("cx", d => d.cx).attr("cy", d => d.cy).attr("r", d => d.r)
            .attr("fill", "#ffffff")
            .attr("stroke", "#0f172a")
            .attr("stroke-width", "2.2px");

        stateNodes.append("image")
            .attr("xlink:href", d => `images/${d.d.abbr}_shape.png`)
            .attr("x", d => d.cx - 13).attr("y", d => d.cy - 13).attr("width", 26).attr("height", 26)
            .style("pointer-events", "none");

        stateNodes.append("text")
            .attr("class", "state-name-text")
            .attr("x", d => d.lx).attr("y", d => d.ly + 4).attr("text-anchor", d => d.anchor)
            .style("pointer-events", "all")
            .style("cursor", "pointer")
            .text(d => d.d.state);

        window.updateStateDelegationChart = function (newMode) {
            currentStateMode = newMode;
            positions = getPositions(currentStateMode);

            stateNodes.data(positions, d => d.d.abbr).each(function (d) {
                const g = d3.select(this);
                g.select("circle").transition().duration(500).attr("cy", d.cy);
                g.select("image").transition().duration(500).attr("x", d.cx - 13).attr("y", d.cy - 13);
                g.select("text.state-name-text").transition().duration(500).attr("x", d.lx).attr("y", d.ly + 4);
                g.selectAll("line")
                    .attr("opacity", Math.hypot(d.lx - d.cx, d.ly - d.cy) > (d.r + 14) ? 0.85 : 0)
                    .transition().duration(500)
                    .attr("x1", d.cx).attr("y1", d.cy).attr("x2", d.lx).attr("y2", d.ly);
            });
        };
    }

    // =========================================================================
    // 3. MASTER SCENARIO TOGGLE CONTROLLER
    // =========================================================================
    document.querySelectorAll(".scenario-btn").forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            document.querySelectorAll(".scenario-btn").forEach(b => b.classList.remove("active"));
            this.classList.add("active");
            const selectedMode = this.getAttribute("data-mode");

            const envText = selectedMode === "neutral"
                ? "Active Environment: Neutral"
                : "Active Environment: 2026 Midterm (D+8.0)";

            const envColor = selectedMode === "neutral" ? "#475569" : "#2563eb";

            const lbl1 = document.getElementById("chart1-env-label");
            const lbl2 = document.getElementById("chart2-env-label");

            if (lbl1) { lbl1.textContent = envText; lbl1.style.color = envColor; }
            if (lbl2) { lbl2.textContent = envText; lbl2.style.color = envColor; }

            if (typeof window.updateGerrymanderChart === "function") {
                window.updateGerrymanderChart(selectedMode);
            }
            if (typeof window.updateStateDelegationChart === "function") {
                window.updateStateDelegationChart(selectedMode);
            }
        });
    });
});
