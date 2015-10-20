# Embedded file name: C:\Development\routeless-server\config.py
import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SSL_DISABLE = False
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    PERFVIZ_MAIL_SUBJECT_PREFIX = '[PerfViz]'
    PERFVIZ_MAIL_SENDER = 'Performance Visualizer <me@brianschoolcraft.com>'
    PERFVIZ_ADMIN = os.environ.get('PERFVIZ_ADMIN')
        
    UPLOAD_FOLDER = os.path.join('perfviz', 'files')
    ALLOWED_EXTENSIONS = set(['tcx', 'gpx'])

    @staticmethod
    def init_app(app):
        pass


class ProductionConfig(Config):

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT), fromaddr=cls.FLASKY_MAIL_SENDER, toaddrs=[cls.FLASKY_ADMIN], subject=cls.FLASKY_MAIL_SUBJECT_PREFIX + ' Application Error', credentials=credentials, secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)
        return

class UnixConfig(ProductionConfig):

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

class DevelopmentConfig(Config):
    DEBUG = True

class DevServerConfig(UnixConfig):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False

config = {'development': DevelopmentConfig,
 'dev_server': DevServerConfig,
 'testing': TestingConfig,
 'production': ProductionConfig,
 'unix': UnixConfig,
 'default': DevelopmentConfig}