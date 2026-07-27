document.addEventListener("DOMContentLoaded", function() {
    // 1. Move the Layer Control box into our Header Wrapper
    var checkControlInterval = setInterval(function() {
        var nativeControl = document.querySelector('.leaflet-control-layers');
        var targetAnchor = document.getElementById('toggle-anchor-zone');
        
        if (nativeControl && targetAnchor) {
            clearInterval(checkControlInterval);
            targetAnchor.appendChild(nativeControl);
        }
    }, 100);

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
