import os
from dotenv import load_dotenv

# تحميل المتغيرات البيئية من ملف .env
load_dotenv()

class Config:
    """الإعدادات الأساسية المشتركة بين جميع البيئات"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # إعدادات البريد الإلكتروني
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or MAIL_USERNAME

    # إعدادات رفع الملفات
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # الحد الأقصى لحجم الملف (16 ميجابايت)
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar'
    }

    @staticmethod
    def init_app(app):
        """تهيئة التطبيق بالإعدادات"""
        pass


class DevelopmentConfig(Config):
    """إعدادات بيئة التطوير"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'correspondence.db')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # تعيين مجلد التحميل في بيئة التطوير
        app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads/attachments')

        # التأكد من وجود المجلدات اللازمة
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(os.path.join(app.static_folder, 'uploads/profile_images'), exist_ok=True)
        os.makedirs(os.path.join(app.static_folder, 'uploads/signatures'), exist_ok=True)


class TestingConfig(Config):
    """إعدادات بيئة الاختبار"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'test.db')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # تعيين مجلد التحميل في بيئة الاختبار
        app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads/test/attachments')

        # التأكد من وجود المجلدات اللازمة
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(os.path.join(app.static_folder, 'uploads/test/profile_images'), exist_ok=True)
        os.makedirs(os.path.join(app.static_folder, 'uploads/test/signatures'), exist_ok=True)


class ProductionConfig(Config):
    """إعدادات بيئة الإنتاج"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'correspondence.db')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # تعيين مجلد التحميل في بيئة الإنتاج
        app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER') or \
            os.path.join(app.static_folder, 'uploads/attachments')

        # التأكد من وجود المجلدات اللازمة
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(os.path.join(app.static_folder, 'uploads/profile_images'), exist_ok=True)
        os.makedirs(os.path.join(app.static_folder, 'uploads/signatures'), exist_ok=True)


# تكوين القاموس للإعدادات المتاحة
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig
}
