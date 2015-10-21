import pandas as pd
import geojson

import numpy as np
from xml.dom import minidom
import datetime
from geopy.distance import distance
import utm
from bokeh.plotting import figure, vplot, ColumnDataSource
from bokeh.models import HoverTool
from collections import OrderedDict

import dateutil

import utm

import folium
from shapely.geometry import Point

def xml_to_float(element):
    if element is not None:
        return float(element[0].firstChild.data)
    else:
        return np.nan
        
def xml_to_time(element):
    if element is not None:
        # return datetime.datetime.strptime(element[0].firstChild.data, '%Y-%m-%dT%H:%M:%S.%fZ')
        return dateutil.parser.parse(element[0].firstChild.data)
    else:
        return np.nan
    
def diff_time_array(array):
    out = np.concatenate([np.ones(1, dtype=np.diff(array).dtype), np.diff(array)])
    out[out==0] = np.ones(out[out==0].shape, dtype=np.diff(array).dtype)
    return out

def diff_array(array):
    out = np.concatenate([[0], np.diff(array)])
    out[out==0] = np.nan
    return out

def calc_distance(lats, lons):
    distances = [0]
    bad = None
    for lat1, lon1, lat2, lon2 in zip(lats[0:-1], lons[0:-1], lats[1:], lons[1:]):
        try:
            distances.append(distance((lat1, lon1), (lat2, lon2)).meters)
        except Exception as e:
            print e
            import traceback
            # print traceback.print_exc(e)
            #import pdb; pdb.set_trace()
            distances.append(0)
    return distances
    
def strip_units(a):
    return np.array([v.value for v in a])
    
def embed(fmaps, titles=[], width='100%', height='510px', *args, **kwargs):
    """
    Embeds a folium map in a IPython/Jupyter notebook.
    This method will not work if the map depends on any files (json data). Also this uses
    the HTML5 srcdoc attribute, which may not be supported in all browsers.
    fmaps -- a single folium map or an iterable containing folium maps
    """
    from IPython.display import HTML
    template = '<h4>{title}</h4><iframe srcdoc="{srcdoc}" style="width: {width}; height: {height}; border: none"></iframe>'
    html = ''
    try:
        for fmap, title in zip(fmaps, titles):
            fmap._build_map()
            html += template.format(
                title=title,
                srcdoc=fmap.HTML.replace('"', '&quot;'),
                height=str(height),
                width=str(width),
            )
    except TypeError:
        fmap = fmaps
        fmap._build_map()
        html = template.format(
            srcdoc=fmap.HTML.replace('"', '&quot;'),
            height=str(height),
            width=str(width),
        )
    return HTML(html)

class GPSPlotter(object):
    def __init__(self, hr_zones=None):      
        
        if hr_zones is not None:
            self.hr_zones = hr_zones
        else:
            self.hr_zones = {'Biking': [0, 113, 149, 167, 185, 200],
                             'Running': [0, 124, 154, 170, 185, 200]}
                             
        self.suffer_score_weights = {'Biking': [12.,24.,45.,100.,120.],
                                     'Running': [18.,65.,110.,250.,275.]}
        
    # def unitless_df(self):
        
    def import_TCX(self, filename):    
       
        doc = minidom.parse(filename)
        doc.normalize()
        self.tcx = doc.documentElement   
            
        points = []
        for lap in self.tcx.getElementsByTagName('Lap'):
            for track in lap.getElementsByTagName('Track'):
                for trackpoint in track.getElementsByTagName('Trackpoint'):     

                    _pos = trackpoint.getElementsByTagName('Position') or None
                    if _pos:
                        _lat = _pos[0].getElementsByTagName('LatitudeDegrees')
                        _lon = _pos[0].getElementsByTagName('LongitudeDegrees')
                    else:
                        _lat = None
                        _lon = None

                    _time = trackpoint.getElementsByTagName('Time')
                    _dist = trackpoint.getElementsByTagName('DistanceMeters') or None
                    _alt = trackpoint.getElementsByTagName('AltitudeMeters') or None

                    _hr_cont = trackpoint.getElementsByTagName('HeartRateBpm') or None
                    if _hr_cont:
                        _hr = _hr_cont[0].getElementsByTagName('Value') or None
                    else:
                        _hr = None

                    _cad = trackpoint.getElementsByTagName('Cadence') or None



                    _point = {'lat': xml_to_float(_lat),
                              'lon': xml_to_float(_lon),
                              'time': xml_to_time(_time),
                              'alt':  xml_to_float(_alt),
                              'hr':   xml_to_float(_hr),
                              'cad':  xml_to_float(_cad),
                              'dist': xml_to_float(_dist),
                             }
                    points.append(_point)
                    
        self.points = points
        # self.activity_type = self.tcx.getElementsByTagName('Activity')[0].attributes.getNamedItem('Sport')
        self.activity_type = 'Biking'
        
    def import_GPX(self, filename):    
    
        doc = minidom.parse(filename)
        doc.normalize()
        self.gpx = doc.documentElement   

        points = []
        for track in self.gpx.getElementsByTagName('trk'):
            for seg in track.getElementsByTagName('trkseg'):
                for trackpoint in seg.getElementsByTagName('trkpt'):
                    _lat = trackpoint.attributes.getNamedItem('lat') or None
                    _lon = trackpoint.attributes.getNamedItem('lon') or None
                    _alt = trackpoint.getElementsByTagName('ele') or None
                    _time = trackpoint.getElementsByTagName('time') or None
                    
                    _param_cont = trackpoint.getElementsByTagName('gpxtpx:TrackPointExtension') or None
                    if _param_cont:
                        _hr = _param_cont[0].getElementsByTagName('gpxtpx:hr') or None   
                        _cad = _param_cont[0].getElementsByTagName('gpxtpx:cad') or None   
                    else:
                        _hr = None
                        _cad = None
                    
                    _dist = None
                                        
                    _point = {'lat': float(_lat.value),
                              'lon': float(_lon.value),
                              'time': xml_to_time(_time),
                              'alt':  xml_to_float(_alt),
                              'hr':   xml_to_float(_hr),
                              'cad':  xml_to_float(_cad),
                              'dist': xml_to_float(_dist),
                             }
                    
                    points.append(_point)

        self.points = points
        self.activity_type = 'Biking'
        
    def create_df(self):
        df = pd.DataFrame(self.points)
        
        #Remove duplicate times
        df = df.drop_duplicates(['time']) 
        
        #Drop nans in lat/lon
        df = df[np.isfinite(df['lat'])]
        df = df[np.isfinite(df['lon'])]
        
        df.time = df.time.astype('datetime64[s]')
                
        if np.sum(~pd.isnull(df.time)) > 0:
            df['dtime'] = diff_time_array(df.time) / np.timedelta64(1, 's')
        else:
            df['dtime'] = 1
        #df['dclimb'] = np.max([np.zeros(df.dalt.shape), df.dalt], axis=0)

        df['gps_ddist'] = [v for v in calc_distance(df.lat, df.lon)]
        df['gps_dist'] = np.cumsum(df.gps_ddist)
        
        if sum(pd.notnull(df.dist)) == 0:
            df.dist = df.gps_dist.copy()

        if np.sum(~pd.isnull(df.dist)) > 0:
            temp = diff_array(df.dist).copy()
        else:
            temp = df.gps_ddist.copy()

        temp[temp==0] = np.nan
        df.ddist = temp.copy()


        df['dalt'] = diff_array(df.alt)
        df['speed'] = df.ddist / df.dtime


        df['grade'] = df.dalt / df.ddist

        #df['cumclimb'] = np.cumsum(df.dclimb)

        ## Calc UTM data
        eastings = []
        northings = []
        zones = []
        letters = []

        for lat, lon in zip(df.lat, df.lon):
            try:
                e, n, z, l = utm.from_latlon(lat, lon)
            except Exception as e:
                print e
                import traceback
                # print traceback.print_exc(e)
                #import pdb; pdb.set_trace()
                e, n, z, l = (np.nan,)*4

            eastings.append(e)
            northings.append(n)
            zones.append(z)
            letters.append(l)

        df['easting'] = eastings
        df['northing'] = northings
        df['zone'] = zones
        df['z_letter'] = letters  

        # df = df.set_index('time')
        self.df = df[~np.isnan(df.lat)]
        
    def calc_colors(self, col):
        # import pdb; pdb.set_trace()
        if sum(~np.isnan(col)) > 0:
            _min = np.percentile(col[~np.isnan(col)], 3)
            _max = np.percentile(col[~np.isnan(col)], 97)

            print _min, _max

            bins, edges = np.histogram(col, 254, range=(_min, _max))
            z_bins = np.digitize(col, edges)

            colors = ["#%02x%02x%02x" % (r, g, 0) for r, g in zip(z_bins, 255-z_bins)]
            colors = np.array(colors)
            colors[np.where(np.isnan(col))] = "#%02x%02x%02x" % (155, 155, 155)
        
        else:
            colors = ["#%02x%02x%02x" % (155, 155, 155)] * col.shape[0]
        
        return colors
        
    def create_geojson(self):
        self.df['hr_colors'] = self.calc_colors(self.df.hr)
        self.df['alt_colors'] = self.calc_colors(self.df.alt)
        self.df['cad_colors'] = self.calc_colors(self.df.cad)
        
        # Converting NaN to None for JSON serialization -- NEEDS CLEANUP
        geo_df = self.df.copy()
        geo_df = geo_df.where((pd.notnull(geo_df)), None)


        #temp = self.df.apply(lambda row: geojson.Point([row['lon'], row['lat']]), axis=1)


        feature_list = []
        for row in geo_df.iterrows():
            point = geojson.Point([row[1].lon, row[1].lat])
            feature = geojson.Feature(geometry=point, properties={            
                                             'dist': row[1].dist,
                                             'hr': row[1].hr,
                                             'hr_color': row[1].hr_colors,
                                             'alt': row[1].alt,
                                             'alt_color': row[1].alt_colors,
                                             'cad': row[1].cad,
                                             'cad_color': row[1].cad_colors
                                            })
            feature_list.append(feature)
            
        feature_collection = geojson.FeatureCollection(feature_list)
        self.geojson = geojson.dumps(feature_collection, sort_keys=True)
        
    def create_plots(self):
        df = self.df
        
        s1 = figure(height=350)
        # s1.circle(df.speed, df.hr)
        s1.line(df.lon, df.lat)
        #p.circle(df.speed, df.dtime.astype('timedelta64[s]'))
        
        s2 = figure(height=350, x_axis_type='datetime')
        s2.line(df.dist, df.speed*2.236936)
        s2.line(df.dist, df.gps_speed*2.236936, color='red')

        s3 = figure(height=350, x_axis_type='datetime')
        s3.line(df.time, df.dist)
        s3.line(df.time, df.gps_dist, color='red')

        p = vplot(s1, s2, s3)
        
        return p
        
    def create_color_plot(self, x, y, z, radius, units, title=None, x2=None, y2=None):
        temp = np.copy(z)
        # temp[np.isnan(temp)] = 0
        # temp[np.isinf(temp)] = 0

        _min = np.percentile(z[~np.isnan(z)], 3)
        _max = np.percentile(z[~np.isnan(z)], 97)

        print _min, _max

        bins, edges = np.histogram(temp, 254, range=(_min, _max))
        z_bins = np.digitize(z, edges)

        colors = ["#%02x%02x%02x" % (r, g, 0) for r, g in zip(z_bins, 255-z_bins)]
        colors = np.array(colors)
        colors[np.isnan(z)] = "#%02x%02x%02x" % (155, 155, 155)
        
        
        source = ColumnDataSource(
                    data = dict(
                        x=x,
                        y=y,
                        z=z,
                        z_bins=z_bins,
                        x2=x2,
                        y2=y2,
                        color=colors
                    )
                )

        TOOLS="pan,wheel_zoom,box_zoom,reset,hover,save"

        s1 = figure(title=title, tools=TOOLS)
        s1.circle('x', 'y', 
                  fill_color='color', 
                  line_color=None, 
                  radius=radius, 
                  source=source)    

        hover = s1.select(dict(type=HoverTool))
        hover.point_policy = "follow_mouse"
        hover.tooltips = OrderedDict([
            (title, "@z %s" % units['z']['label']),
            ("(Lon, Lat)", "(@x2, @y2)"),
        ])
        
        s2 = figure(title=title)
        s2.circle(z, z_bins, fill_color=colors, line_color=None, size=5)
        
        
        # Folium map
        lflt = folium.Map(location=[39.091, -85.232], 
                          zoom_start=15,
                          tiles='Stamen Terrain')

        for lon, lat, val, c in zip(x2, y2, z, colors):
            lflt.circle_marker(location=[lat, lon],
                              radius=10,
                              fill_color=c,
                              line_color=None,
                              popup=str(val),
                              fill_opacity=0.9)
        
        p = vplot(s1, s2)
        
        return s1, lflt
        
    def calc_suffer_score(self):
        df = self.df
        
        hr_zones = self.hr_zones[self.activity_type]
        suffer_score_weights = self.suffer_score_weights[self.activity_type]

        zone_times = np.histogram(df.hr, 
                                  bins=hr_zones, 
                                  weights=df.dtime
                                 )[0]
                                 
        suffer_score = np.sum(zone_times.astype(float)/3600.*suffer_score_weights)
        
        self.hr_zone_times = zone_times
        self.suffer_score = suffer_score
        
        

