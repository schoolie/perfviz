$(document).ready(function(){
    
    var getParameterByName = function(name) {
        name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
        var regex = new RegExp("[\\?&]" + name + "=([^&#]*)"),
            results = regex.exec(location.search);
        return results === null ? "" : decodeURIComponent(results[1].replace(/\+/g, " "));
    }

    console.log('loaded');
  
  // load a tile layer
    var ocm = L.tileLayer('http://{s}.tile.opencyclemap.org/cycle/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenCycleMap, ' + 'Map data '
    });
    
    var osm = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>'
	});
  
    var caltopo = L.tileLayer('http://s3-us-west-1.amazonaws.com/caltopo/topo/{z}/{x}/{y}.png?v=1', {
		attribution: 'caltopo',
        minZoom: 5,
        maxZoom: 16,
	});
    
    var baseMaps = {
        'OpenStreetMap': osm,
        'OpenCycleMap': ocm,
        'CalTopo': caltopo
    };
    
    // initialize the map
    var map = L.map('map', {
        center: [39.092, -85.23645915091038],
        zoom: 15,
        layers: [osm, ocm]
    });

    L.control.layers(baseMaps).addTo(map);
    
    var cursorMarker = L.circleMarker([39.092, -85.23645915091038], 
                                  {radius: 10,
                                   color: '#0000FF'})        
    
    
    $.ajax({
      dataType: "json",
      url: "http://localhost:5000/get_data/"+ getParameterByName('filename'),
      success: function(data) {
                console.log('data:')
                console.log(data);
                plot_course(data, map)
            },
      error: function(xhr,status,error) {
        console.log('error');
        console.log(xhr);
        console.log(status);
        console.log(error);
        
        }
    });
    
    function onEachFeature(feature, layer) {
        // does this feature have a property named popupContent?
        if (feature.properties) {
            layer.bindPopup(feature.properties.cad);
            console.log(feature.properties.cad);
        }
    }
    
    var hr_array = ['hr'];
    var cad_array = ['cad'];
    var dist_array = ['dist'];
    var alt_array = ['alt'];
    var lat_array = ['lat'];
    var lon_array = ['lon'];
    var dist_bounds = [0,9999999999999];
    
    var small_rad = 2;
    var large_rad = 4;
    
    function extractData(feature) {
        cad_array.push(feature.properties.cad);
        hr_array.push(feature.properties.hr);
        dist_array.push(feature.properties.dist);
        alt_array.push(feature.properties.alt);
        
        lon_array.push(feature.geometry.coordinates[0]);
        lat_array.push(feature.geometry.coordinates[1]);
    }
    
    function debounce(func, wait, immediate) {
        var timeout;
        return function() {
            var context = this, args = arguments;
            var later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            var callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    };
    

    
    plot_course = function(data, map) {
        

        
        var create_geoJsonLayer = function(param, bounds, radius, color, border_weight) {
            var def_color = color || null;
            var def_radius = radius || small_rad;
            var border_weight = border_weight || 0
            
            var color = def_color;
            var radius = def_radius;
            
            var geoJsonLayer = L.geoJson(data, {
                pointToLayer: function (feature, latlng) {
                    var hr = feature.properties.hr;
                    var hr_color = feature.properties.hr_color;
                    var cad = feature.properties.cad;
                    var cad_color = feature.properties.cad_color;
                    return L.circleMarker(latlng).bindPopup('<p>Cadence: ' + cad + '</p><p>HR: ' + hr + '</p>');

                },
                style: function(feature, layer) {
                    if (def_color) {
                        color = def_color;
                    }
                    else {
                        color = feature.properties[''+param+'_color'];
                    }
                    return {radius: radius,
                            fillColor: color,
                            color: "#000",
                            weight: border_weight,
                            opacity: 1,
                            fillOpacity: 0.9
                    }
                },
                filter: function(feature, layer) {
                    return feature.properties.dist < bounds[1] && feature.properties.dist > bounds[0];
                }
            })
            
            return geoJsonLayer;
        }
        
        var greyLayer = create_geoJsonLayer('hr', [0,9999999999999], small_rad, '#888');
        greyLayer.addTo(map);        
        
        var colorLayer = create_geoJsonLayer('hr', dist_bounds, large_rad);
        colorLayer.addTo(map);
        map.fitBounds(colorLayer.getBounds());    

        var border_weight = 0
        var onBaseLayerChange = function(layer) {
            
            border_weight = 0;
            
            if (layer.name === 'CalTopo') {
                border_weight = 1;
            }
            
            map.removeLayer(greyLayer);
            map.removeLayer(colorLayer);

            greyLayer = create_geoJsonLayer('hr', [0,9999999999999], small_rad, color='#888', border_weight=border_weight);
            greyLayer.addTo(map);        
            
            colorLayer = create_geoJsonLayer('hr', dist_bounds, large_rad, color=null, border_weight=border_weight);
            colorLayer.addTo(map);
            
            if (map.getMaxZoom() < map.getZoom()) {
                map.setZoom(map.getMaxZoom());
            }
        }
        
        map.on('baselayerchange', onBaseLayerChange);
        
        // Convert geoJson to arrays for chart
        data.features.forEach(function(feature){
            extractData(feature);
        })
        console.log(lat_array);
        
        var lazyLayerCreate = debounce(function(domain){
            dist_bounds = domain;
            
            map.removeLayer(colorLayer);
            console.log(border_weight);
            colorLayer = create_geoJsonLayer('hr', dist_bounds, large_rad, color=null, border_weight=border_weight);
            colorLayer.addTo(map);
            
            map.fitBounds(colorLayer.getBounds());
            
        }, 250);
        
        var chart = c3.generate({
            data: {
                columns: [
                    dist_array,
                    hr_array,
                    cad_array,
                    alt_array,
                ],                
                axes: {
                    hr: 'y',
                    cad: 'y2',
                    alt: 'y'
                },
                x: 'dist',
                types: {
                    hr: 'spline',
                    cad: 'line',
                    alt: 'area-spline'
                },
                onmouseover: function (d) { 
                    lat = lat_array[d.index];
                    lon = lon_array[d.index];      
                    cursorMarker.setLatLng([lat, lon]);
                    cursorMarker.addTo(map);
                },
                onmouseout: function (d) { map.removeLayer(cursorMarker); }},
            point: {show: false},
            axis: {
                x: {
                    label: {
                        text: 'Distance (m)',
                        position: 'outer-center'
                    },
                    tick: {
                        format: function (x) { return Math.round(x, 0); },
                        count: 20,
                    }
                },
                y: {
                    label: {
                        text: 'HR (bpm)',
                        position: 'outer-bottom'
                    }
                },
                y2: {
                    show: true,
                    label: {
                        text: 'Cadence (rpm)',
                        position: 'outer-bottom'
                    }
                }
            },
            subchart: {
                show: true,
                onbrush: function (domain) {
                    lazyLayerCreate(domain);
                    
                }
            },
        });    
    }
    
})