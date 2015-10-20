import os
from flask import Flask, jsonify, Blueprint, render_template, \
                  request, redirect, url_for, current_app, g
                  
from flask.ext.cors import CORS
from werkzeug import secure_filename

import json

from config import config
from gpx_processing import GPSPlotter

main = Blueprint('main', __name__,
                 template_folder='templates')


    
    
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in current_app.config['ALLOWED_EXTENSIONS']

@main.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('.visualizer', filename=filename))
    return render_template('upload_file.html')

@main.route('/get_data/<filename>')
def get_data(filename):

    gps = GPSPlotter()
    filename = os.path.join('perfviz','files',filename)
    # filename = os.path.join('perfviz','files','BC Epic.tcx')
    
    try:
        ext = filename.split('.')[-1]
        if ext == 'tcx':
            gps.import_TCX(filename)   
        elif ext == 'gpx':
            gps.import_GPX(filename)   
        else:
            return jsonify({'error' : 'Unrecognized File Type'})
            
        
        gps.create_df()    
        gps.create_gdf()        
        os.remove(filename)
        print 'file removed'
        
    except Exception as e:
        print e
        import traceback
        print traceback.print_exc(e)
        
        return jsonify({'error' : e})
        
    return gps.gdf[0:].to_json()
    
@main.route('/visualizer/<filename>')
def visualizer(filename):
    return render_template('visualizer.html', filename=filename)
    # return render_template('testmap.html', filename=filename)
    
cors = CORS()


def create_app(config_name):    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    cors.init_app(app, resources={r"/*": {"origins": "*"}})
    
    app.register_blueprint(main)
    
    return app
