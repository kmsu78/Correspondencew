from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import os
import uuid
import mimetypes
import random
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import secrets
from flask_mail import Mail
from dotenv import load_dotenv
from markupsafe import escape
from config import config

# Load environment variables from .env file
load_dotenv()

# تحديد بيئة التشغيل (development, testing, production)
env = os.environ.get('FLASK_ENV', 'development')

# إنشاء تطبيق Flask
app = Flask(__name__, instance_relative_config=True)

# تطبيق الإعدادات من ملف config.py
app.config.from_object(config[env])
config[env].init_app(app)

# إضافة فلتر nl2br لتحويل السطور الجديدة إلى <br> ودعم محتوى HTML
@app.template_filter('nl2br')
def nl2br(value):
    if value:
        # التحقق مما إذا كان المحتوى يحتوي على وسوم HTML
        if '<' in value and '>' in value:
            # إذا كان المحتوى يحتوي على HTML، نعيده كما هو بدون escape
            return value
        else:
            # إذا كان المحتوى نصًا عاديًا، نقوم بتحويل السطور الجديدة إلى <br>
            value = escape(value)
            return value.replace('\n', '<br>\n')
    return value

# وظائف مساعدة للملفات المرفقة
def allowed_file(filename):
    """التحقق من أن امتداد الملف مسموح به"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_attachment(file):
    """حفظ الملف المرفق وإنشاء سجل له في قاعدة البيانات"""
    if file and file.filename:
        # تأمين اسم الملف
        original_filename = secure_filename(file.filename)

        # إنشاء اسم فريد للملف باستخدام UUID
        file_ext = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"

        # تحديد مسار الملف
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        # حفظ الملف
        file.save(file_path)

        # تحديد نوع الملف
        file_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'

        # إنشاء كائن Attachment
        attachment = Attachment(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_type=file_type
        )

        return attachment

    return None

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'الرجاء تسجيل الدخول للوصول إلى هذه الصفحة'

# Department model
class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # العلاقة مع المستخدمين
    users = db.relationship('User', backref='dept', lazy='dynamic')

    def get_users_count(self):
        """الحصول على عدد المستخدمين في القسم"""
        return self.users.count()

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    department_name = db.Column(db.String(80))  # للتوافق مع الإصدارات السابقة
    role = db.Column(db.String(20))  # للتوافق مع الإصدارات السابقة
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))  # الدور الجديد
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_expiry = db.Column(db.DateTime)

    # معلومات الملف الشخصي الإضافية
    full_name = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    position = db.Column(db.String(100))
    bio = db.Column(db.Text)
    profile_image = db.Column(db.String(200))
    signature = db.Column(db.Text)  # توقيع المستخدم للرسائل (نص)
    signature_image = db.Column(db.String(200))  # مسار صورة التوقيع

    # إعدادات النظام
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(10), default='ar')
    notifications_enabled = db.Column(db.Boolean, default=True)

    # صلاحيات إدارة الحالات (للتوافق مع الإصدارات السابقة)
    can_change_status = db.Column(db.Boolean, default=False)  # صلاحية تغيير حالة الرسائل
    can_manage_status_permissions = db.Column(db.Boolean, default=False)  # صلاحية إدارة صلاحيات تغيير الحالة

    # العلاقة مع سجل تغييرات الصلاحيات
    permission_changes_received = db.relationship('PermissionChange', foreign_keys='PermissionChange.user_id', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    permission_changes_made = db.relationship('PermissionChange', foreign_keys='PermissionChange.changed_by_id', backref='changed_by', lazy='dynamic')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()
        return self.reset_token

    def is_admin(self):
        """التحقق مما إذا كان المستخدم مشرفًا"""
        # للتوافق مع الإصدارات السابقة
        if self.role == 'admin':
            return True
        # التحقق من الدور الجديد
        if self.role_obj and self.role_obj.name == 'admin':
            return True
        return False

    def has_permission(self, permission_name):
        """التحقق مما إذا كان المستخدم يملك صلاحية معينة"""
        # المشرفون لديهم جميع الصلاحيات
        if self.is_admin():
            return True
        # التحقق من صلاحيات الدور
        if self.role_obj:
            return self.role_obj.has_permission(permission_name)
        return False

    def has_status_permission(self):
        """التحقق مما إذا كان المستخدم لديه صلاحية تغيير حالة الرسائل"""
        # للتوافق مع الإصدارات السابقة
        if self.is_admin():
            return True
        if self.can_change_status:
            return True
        # التحقق من الصلاحيات الجديدة
        return self.has_permission('change_message_status')

    def has_status_management_permission(self):
        """التحقق مما إذا كان المستخدم لديه صلاحية إدارة صلاحيات تغيير الحالة"""
        # للتوافق مع الإصدارات السابقة
        if self.is_admin():
            return True
        if self.can_manage_status_permissions:
            return True
        # التحقق من الصلاحيات الجديدة
        return self.has_permission('manage_permissions')

# Message model
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # للتوافق مع الإصدارات السابقة
    status = db.Column(db.String(20), default='new')  # للتوافق مع الإصدارات السابقة
    category = db.Column(db.String(50))
    is_archived = db.Column(db.Boolean, default=False)  # للتوافق مع الإصدارات السابقة
    has_attachments = db.Column(db.Boolean, default=False)

    # حقول جديدة للمستلمين المتعددين
    is_multi_recipient = db.Column(db.Boolean, default=False)  # هل الرسالة لها مستلمين متعددين
    recipient_type = db.Column(db.String(20), default='user')  # نوع المستلم (user, group, multiple)

    # حقول أخرى
    priority = db.Column(db.String(20), default='normal')  # عادي، عاجل، هام جداً
    message_type = db.Column(db.String(30))  # مذكرة، تعميم، طلب، إخطار، incoming
    confidentiality = db.Column(db.String(20), default='normal')  # عام، سري، سري للغاية
    reference_number = db.Column(db.String(50))  # رقم مرجعي للرسالة
    due_date = db.Column(db.Date)  # تاريخ الاستحقاق أو الموعد النهائي
    sender_entity = db.Column(db.String(200))  # الجهة المرسلة (للرسائل الواردة)

    # إضافة العلاقات
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')  # للتوافق مع الإصدارات السابقة
    attachments = db.relationship('Attachment', backref='message', lazy='dynamic', cascade='all, delete-orphan')
    status_changes = db.relationship('MessageStatusChange', backref='message', lazy='dynamic', cascade='all, delete-orphan')
    recipients_data = db.relationship('MessageRecipient', backref='message', cascade='all, delete-orphan')

    # دوال مساعدة للمستلمين المتعددين
    def get_recipients(self):
        """الحصول على قائمة المستلمين"""
        if not self.is_multi_recipient:
            return [self.recipient] if self.recipient else []

        recipients_data = MessageRecipient.query.filter_by(message_id=self.id).all()
        return [r.recipient for r in recipients_data]

    def add_recipient(self, recipient_id, recipient_type='user'):
        """إضافة مستلم للرسالة"""
        # التحقق من عدم وجود المستلم بالفعل
        existing = MessageRecipient.query.filter_by(
            message_id=self.id,
            recipient_id=recipient_id
        ).first()

        if existing:
            return False

        # إضافة المستلم
        recipient_data = MessageRecipient(
            message_id=self.id,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            status='new'
        )

        db.session.add(recipient_data)
        self.is_multi_recipient = True
        db.session.commit()
        return True

    def add_group_recipients(self, group_id):
        """إضافة جميع أعضاء المجموعة كمستلمين"""
        group = UserGroup.query.get(group_id)
        if not group:
            return False

        # الحصول على أعضاء المجموعة
        members = group.get_members()
        added = False

        for member in members:
            # تجاهل المرسل نفسه
            if member.id == self.sender_id:
                continue

            # إضافة العضو كمستلم
            recipient_data = MessageRecipient(
                message_id=self.id,
                recipient_id=member.id,
                recipient_type='group',
                status='new'
            )

            db.session.add(recipient_data)
            added = True

        if added:
            self.is_multi_recipient = True
            self.recipient_type = 'group'
            db.session.commit()

        return added

    def get_status_display(self):
        """الحصول على النص العربي لحالة الرسالة"""
        status_map = {
            'new': 'جديد',
            'read': 'مقروء',
            'replied': 'تم الرد',
            'processing': 'قيد المعالجة',
            'completed': 'مكتمل',
            'closed': 'مغلق',
            'postponed': 'مؤجل'
        }
        return status_map.get(self.status, self.status)

    def get_status_color(self):
        """الحصول على لون حالة الرسالة"""
        status_colors = {
            'new': 'primary',
            'read': 'success',
            'replied': 'info',
            'processing': 'warning',
            'completed': 'success',
            'closed': 'secondary',
            'postponed': 'danger'
        }
        return status_colors.get(self.status, 'secondary')

    def get_priority_display(self):
        """الحصول على النص العربي لأولوية الرسالة"""
        priority_map = {
            'normal': 'عادي',
            'urgent': 'عاجل',
            'very_urgent': 'هام جداً'
        }
        return priority_map.get(self.priority, self.priority)

    def get_priority_color(self):
        """الحصول على لون أولوية الرسالة"""
        priority_colors = {
            'normal': 'success',
            'urgent': 'warning',
            'very_urgent': 'danger'
        }
        return priority_colors.get(self.priority, 'secondary')

    def get_message_type_display(self):
        """الحصول على النص العربي لنوع الرسالة"""
        type_map = {
            'memo': 'مذكرة',
            'circular': 'تعميم',
            'request': 'طلب',
            'notification': 'إخطار',
            'report': 'تقرير',
            'invitation': 'دعوة',
            'other': 'أخرى'
        }
        return type_map.get(self.message_type, self.message_type)

    def get_confidentiality_display(self):
        """الحصول على النص العربي لمستوى سرية الرسالة"""
        confidentiality_map = {
            'normal': 'عام',
            'confidential': 'سري',
            'highly_confidential': 'سري للغاية'
        }
        return confidentiality_map.get(self.confidentiality, self.confidentiality)

    def get_confidentiality_color(self):
        """الحصول على لون مستوى سرية الرسالة"""
        confidentiality_colors = {
            'normal': 'success',
            'confidential': 'warning',
            'highly_confidential': 'danger'
        }
        return confidentiality_colors.get(self.confidentiality, 'secondary')

    def change_status(self, new_status, user_id, notes=None, recipient_id=None):
        """تغيير حالة الرسالة وتسجيل التغيير"""
        # إذا كانت الرسالة متعددة المستلمين وتم تحديد مستلم
        if self.is_multi_recipient and recipient_id:
            recipient_data = MessageRecipient.query.filter_by(
                message_id=self.id,
                recipient_id=recipient_id
            ).first()

            if recipient_data:
                if recipient_data.status == new_status:
                    return False

                old_status = recipient_data.status
                recipient_data.status = new_status

                # تحديث تاريخ القراءة إذا كانت الحالة الجديدة هي "مقروء"
                if new_status == 'read' and not recipient_data.read_at:
                    recipient_data.read_at = datetime.now()

                # إنشاء سجل تغيير الحالة
                status_change = MessageStatusChange(
                    message_id=self.id,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by_id=user_id,
                    notes=notes,
                    recipient_id=recipient_id
                )

                db.session.add(status_change)
                return True
            return False

        # للتوافق مع الإصدارات السابقة (رسالة بمستلم واحد)
        if self.status == new_status:
            return False

        old_status = self.status
        self.status = new_status

        # إنشاء سجل تغيير الحالة
        status_change = MessageStatusChange(
            message_id=self.id,
            old_status=old_status,
            new_status=new_status,
            changed_by_id=user_id,
            notes=notes
        )

        db.session.add(status_change)
        return True

# نموذج البريد الشخصي
class PersonalMail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # المستخدم المالك
    title = db.Column(db.String(200), nullable=False)  # عنوان البريد الشخصي
    content = db.Column(db.Text)  # محتوى البريد
    source = db.Column(db.String(200))  # مصدر البريد (من أين)
    reference_number = db.Column(db.String(100))  # الرقم المرجعي
    date = db.Column(db.DateTime, default=datetime.utcnow)  # تاريخ الإضافة
    due_date = db.Column(db.Date)  # تاريخ الاستحقاق
    status = db.Column(db.String(20), default='pending')  # حالة البريد (pending, in_progress, completed, cancelled)
    priority = db.Column(db.String(20), default='normal')  # أولوية البريد (normal, urgent, very_urgent)
    notes = db.Column(db.Text)  # ملاحظات إضافية
    has_attachments = db.Column(db.Boolean, default=False)  # هل يحتوي على مرفقات
    is_archived = db.Column(db.Boolean, default=False)  # هل تم أرشفته

    # العلاقات
    user = db.relationship('User', backref='personal_mails')
    attachments = db.relationship('PersonalMailAttachment', backref='personal_mail', lazy='dynamic', cascade='all, delete-orphan')

    def get_status_display(self):
        """الحصول على النص العربي لحالة البريد الشخصي"""
        status_map = {
            'pending': 'قيد الانتظار',
            'in_progress': 'قيد التنفيذ',
            'completed': 'مكتمل',
            'cancelled': 'ملغي'
        }
        return status_map.get(self.status, self.status)

    def get_status_color(self):
        """الحصول على لون حالة البريد الشخصي"""
        status_colors = {
            'pending': 'warning',
            'in_progress': 'info',
            'completed': 'success',
            'cancelled': 'danger'
        }
        return status_colors.get(self.status, 'secondary')

    def get_priority_display(self):
        """الحصول على النص العربي لأولوية البريد الشخصي"""
        priority_map = {
            'normal': 'عادي',
            'urgent': 'عاجل',
            'very_urgent': 'هام جداً'
        }
        return priority_map.get(self.priority, self.priority)

    def get_priority_color(self):
        """الحصول على لون أولوية البريد الشخصي"""
        priority_colors = {
            'normal': 'success',
            'urgent': 'warning',
            'very_urgent': 'danger'
        }
        return priority_colors.get(self.priority, 'secondary')

# نموذج مرفقات البريد الشخصي
class PersonalMailAttachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personal_mail_id = db.Column(db.Integer, db.ForeignKey('personal_mail.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)  # اسم الملف المخزن
    original_filename = db.Column(db.String(255), nullable=False)  # اسم الملف الأصلي
    file_path = db.Column(db.String(500), nullable=False)  # مسار الملف
    file_size = db.Column(db.Integer)  # حجم الملف بالبايت
    file_type = db.Column(db.String(100))  # نوع الملف
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)  # تاريخ الرفع

    def get_size_display(self):
        """عرض حجم الملف بشكل مناسب (KB, MB)"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"

    def get_file_icon(self):
        """الحصول على أيقونة مناسبة لنوع الملف"""
        if not self.file_type:
            return 'fa-file'

        if 'image' in self.file_type:
            return 'fa-file-image'
        elif 'pdf' in self.file_type:
            return 'fa-file-pdf'
        elif 'word' in self.file_type or 'document' in self.file_type:
            return 'fa-file-word'
        elif 'excel' in self.file_type or 'spreadsheet' in self.file_type:
            return 'fa-file-excel'
        elif 'powerpoint' in self.file_type or 'presentation' in self.file_type:
            return 'fa-file-powerpoint'
        elif 'zip' in self.file_type or 'rar' in self.file_type or 'tar' in self.file_type or 'compressed' in self.file_type:
            return 'fa-file-archive'
        elif 'text' in self.file_type:
            return 'fa-file-alt'
        else:
            return 'fa-file'

    def is_viewable_in_browser(self):
        """التحقق مما إذا كان الملف يمكن عرضه في المتصفح"""
        viewable_types = ['image/', 'text/', 'application/pdf']
        return any(vt in self.file_type for vt in viewable_types)

# نموذج سجل تغييرات حالة الرسالة
class MessageStatusChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    old_status = db.Column(db.String(20), nullable=False)
    new_status = db.Column(db.String(20), nullable=False)
    change_date = db.Column(db.DateTime, default=datetime.now)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text)

    # حقل جديد لدعم المستلمين المتعددين
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # المستلم المحدد (في حالة الرسائل متعددة المستلمين)

    # إضافة العلاقات
    changed_by = db.relationship('User', foreign_keys=[changed_by_id], backref='status_changes')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='status_changes_as_recipient')

# نموذج سجل تغييرات الصلاحيات
class PermissionChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # المستخدم الذي تم تغيير صلاحياته
    changed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # المستخدم الذي قام بالتغيير
    permission_type = db.Column(db.String(50), nullable=False)  # نوع الصلاحية (change_status أو manage_permissions)
    old_value = db.Column(db.String(255), nullable=False)  # القيمة القديمة (تم تغييرها من Boolean إلى String لدعم المزيد من أنواع التغييرات)
    new_value = db.Column(db.String(255), nullable=False)  # القيمة الجديدة
    change_date = db.Column(db.DateTime, default=datetime.utcnow)  # تاريخ التغيير
    notes = db.Column(db.Text)  # ملاحظات إضافية

    # حقول جديدة
    permission_id = db.Column(db.Integer, db.ForeignKey('permission.id'))  # الصلاحية التي تم تغييرها (إذا كانت متعلقة بصلاحية محددة)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))  # الدور الذي تم تغييره (إذا كان التغيير متعلق بدور)

    # العلاقات الجديدة
    permission = db.relationship('Permission', backref='changes')
    role = db.relationship('Role', backref='permission_changes')

    def get_permission_display(self):
        """الحصول على النص العربي لنوع الصلاحية"""
        permission_map = {
            'change_status': 'تغيير حالة الرسائل',
            'manage_permissions': 'إدارة صلاحيات المستخدمين',
            'role_change': 'تغيير الدور',
            'permission_add': 'إضافة صلاحية',
            'permission_remove': 'إزالة صلاحية',
            'direct_permission': 'صلاحية مباشرة',
            'role_permission': 'صلاحية دور'
        }

        # إذا كان التغيير متعلق بصلاحية محددة وتم تحديدها
        if self.permission_id and self.permission:
            return f"{permission_map.get(self.permission_type, self.permission_type)}: {self.permission.get_display_name()}"

        return permission_map.get(self.permission_type, self.permission_type)

    def get_value_display(self, is_old=False):
        """الحصول على عرض مناسب للقيمة (القديمة أو الجديدة)"""
        value = self.old_value if is_old else self.new_value

        # إذا كان التغيير متعلق بتغيير الدور
        if self.permission_type == 'role_change':
            if value == 'None':
                return 'بدون دور'

            # محاولة الحصول على اسم الدور
            try:
                role_id = int(value)
                from app import Role
                role = Role.query.get(role_id)
                if role:
                    return role.name
            except:
                pass

            return value

        # إذا كانت القيمة بوليانية (نعم/لا)
        if value.lower() in ['true', '1', 'yes']:
            return 'نعم'
        elif value.lower() in ['false', '0', 'no']:
            return 'لا'

        return value

# نموذج مجموعات الصلاحيات
class PermissionGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # اسم المجموعة (مثل: user_management, message_management)
    display_name = db.Column(db.String(100))  # اسم العرض بالعربية
    description = db.Column(db.String(255))  # وصف المجموعة
    icon = db.Column(db.String(50))  # أيقونة المجموعة (Font Awesome)
    order = db.Column(db.Integer, default=0)  # ترتيب المجموعة

    # العلاقة مع الصلاحيات
    permissions = db.relationship('Permission', backref='group', lazy='dynamic')

# نموذج الصلاحيات
class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # اسم الصلاحية (مثل: manage_users, view_reports)
    display_name = db.Column(db.String(100))  # اسم العرض بالعربية
    description = db.Column(db.String(255))  # وصف الصلاحية
    group_id = db.Column(db.Integer, db.ForeignKey('permission_group.id'))  # مجموعة الصلاحية
    is_critical = db.Column(db.Boolean, default=False)  # هل هي صلاحية حساسة

    # العلاقة مع الأدوار
    roles = db.relationship('Role', secondary='role_permissions', back_populates='permissions')

    def get_display_name(self):
        """الحصول على اسم العرض بالعربية، أو اسم الصلاحية إذا لم يكن متوفرًا"""
        if self.display_name:
            return self.display_name
        return self.name

# نموذج الأدوار
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # اسم الدور (مثل: admin, user, manager)
    description = db.Column(db.String(255))  # وصف الدور
    is_system = db.Column(db.Boolean, default=False)  # هل هو دور نظام (لا يمكن حذفه)

    # العلاقة مع المستخدمين
    users = db.relationship('User', backref='role_obj', lazy='dynamic')

    # العلاقة مع الصلاحيات
    permissions = db.relationship('Permission', secondary='role_permissions', back_populates='roles')

    def has_permission(self, permission_name):
        """التحقق مما إذا كان الدور يملك صلاحية معينة"""
        for permission in self.permissions:
            if permission.name == permission_name:
                return True
        return False

# جدول العلاقة بين الأدوار والصلاحيات
role_permissions = db.Table('role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'), primary_key=True)
)

# نموذج سجل دخول المستخدمين
class UserLoginLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # المستخدم الذي قام بتسجيل الدخول
    login_date = db.Column(db.DateTime, default=datetime.now)  # تاريخ ووقت تسجيل الدخول
    ip_address = db.Column(db.String(50))  # عنوان IP
    user_agent = db.Column(db.String(255))  # معلومات المتصفح
    status = db.Column(db.String(20), default='success')  # حالة تسجيل الدخول (success, failed)

    # العلاقة مع المستخدم
    user = db.relationship('User', backref='login_logs')

# نموذج مجموعة المستخدمين
class UserGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # اسم المجموعة
    description = db.Column(db.Text)  # وصف المجموعة
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # منشئ المجموعة
    created_at = db.Column(db.DateTime, default=datetime.now)  # تاريخ إنشاء المجموعة
    is_active = db.Column(db.Boolean, default=True)  # حالة المجموعة
    is_public = db.Column(db.Boolean, default=True)  # هل المجموعة عامة (يمكن للجميع رؤيتها)

    # العلاقات
    created_by = db.relationship('User', backref='created_groups')
    members = db.relationship('UserGroupMembership', back_populates='group', cascade='all, delete-orphan')

    def get_members_count(self):
        """الحصول على عدد أعضاء المجموعة"""
        return UserGroupMembership.query.filter_by(group_id=self.id).count()

    def get_members(self):
        """الحصول على قائمة أعضاء المجموعة"""
        memberships = UserGroupMembership.query.filter_by(group_id=self.id).all()
        return [membership.user for membership in memberships]

    def add_member(self, user_id, role='member'):
        """إضافة عضو إلى المجموعة"""
        # التحقق من عدم وجود العضو بالفعل
        existing = UserGroupMembership.query.filter_by(group_id=self.id, user_id=user_id).first()
        if existing:
            return False

        # إضافة العضو
        membership = UserGroupMembership(group_id=self.id, user_id=user_id, role=role)
        db.session.add(membership)
        db.session.commit()
        return True

    def remove_member(self, user_id):
        """إزالة عضو من المجموعة"""
        membership = UserGroupMembership.query.filter_by(group_id=self.id, user_id=user_id).first()
        if membership:
            db.session.delete(membership)
            db.session.commit()
            return True
        return False

    def is_member(self, user_id):
        """التحقق مما إذا كان المستخدم عضوًا في المجموعة"""
        return UserGroupMembership.query.filter_by(group_id=self.id, user_id=user_id).first() is not None

    def is_admin(self, user_id):
        """التحقق مما إذا كان المستخدم مشرفًا في المجموعة"""
        membership = UserGroupMembership.query.filter_by(group_id=self.id, user_id=user_id).first()
        return membership and membership.role == 'admin'

# نموذج عضوية المجموعة
class UserGroupMembership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('user_group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), default='member')  # دور المستخدم في المجموعة (member, admin)
    joined_at = db.Column(db.DateTime, default=datetime.now)  # تاريخ الانضمام

    # العلاقات
    group = db.relationship('UserGroup', back_populates='members')
    user = db.relationship('User', backref='group_memberships')

    # تعريف مفتاح فريد مركب لضمان عدم تكرار العضوية
    __table_args__ = (db.UniqueConstraint('group_id', 'user_id', name='_group_user_uc'),)

# نموذج المستخدمين المفضلين
class FavoriteUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # المستخدم الذي أضاف المفضلة
    favorite_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # المستخدم المفضل
    added_at = db.Column(db.DateTime, default=datetime.now)  # تاريخ الإضافة

    # العلاقات
    user = db.relationship('User', foreign_keys=[user_id], backref='favorites')
    favorite_user = db.relationship('User', foreign_keys=[favorite_user_id], backref='favorited_by')

    # تعريف مفتاح فريد مركب لضمان عدم تكرار المفضلة
    __table_args__ = (db.UniqueConstraint('user_id', 'favorite_user_id', name='_user_favorite_uc'),)

# نموذج متلقي الرسالة
class MessageRecipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_type = db.Column(db.String(20), default='user')  # نوع المستلم (user, group)
    status = db.Column(db.String(20), default='new')  # حالة الرسالة لهذا المستلم
    is_archived = db.Column(db.Boolean, default=False)  # هل تم أرشفة الرسالة من قبل هذا المستلم
    read_at = db.Column(db.DateTime)  # تاريخ قراءة الرسالة

    # العلاقات
    recipient = db.relationship('User', backref='received_message_data')

    # تعريف مفتاح فريد مركب لضمان عدم تكرار المستلم للرسالة
    __table_args__ = (db.UniqueConstraint('message_id', 'recipient_id', name='_message_recipient_uc'),)

    def get_status_display(self):
        """الحصول على النص العربي لحالة الرسالة"""
        status_map = {
            'new': 'جديد',
            'read': 'مقروء',
            'replied': 'تم الرد',
            'processing': 'قيد المعالجة',
            'completed': 'مكتمل',
            'closed': 'مغلق',
            'postponed': 'مؤجل'
        }
        return status_map.get(self.status, self.status)

    def get_status_color(self):
        """الحصول على لون حالة الرسالة"""
        status_colors = {
            'new': 'primary',
            'read': 'success',
            'replied': 'info',
            'processing': 'warning',
            'completed': 'success',
            'closed': 'secondary',
            'postponed': 'danger'
        }
        return status_colors.get(self.status, 'secondary')

# نموذج الإشعارات
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # المستخدم المستلم للإشعار
    title = db.Column(db.String(100), nullable=False)  # عنوان الإشعار
    content = db.Column(db.Text, nullable=False)  # محتوى الإشعار
    icon = db.Column(db.String(50), default='fa-bell')  # أيقونة الإشعار
    color = db.Column(db.String(20), default='primary')  # لون الإشعار (primary, success, warning, danger, info)
    created_at = db.Column(db.DateTime, default=datetime.now)  # تاريخ إنشاء الإشعار
    is_read = db.Column(db.Boolean, default=False)  # هل تم قراءة الإشعار
    link = db.Column(db.String(200))  # رابط الإشعار (اختياري)

    # العلاقة مع المستخدم
    user = db.relationship('User', backref='notifications')

# Attachment model
class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # حجم الملف بالبايت
    file_type = db.Column(db.String(100))  # نوع الملف (MIME type)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)

    def get_file_icon(self):
        """تحديد أيقونة الملف بناءً على نوعه"""
        if self.file_type:
            if 'image' in self.file_type:
                return 'fa-file-image'
            elif 'pdf' in self.file_type:
                return 'fa-file-pdf'
            elif 'word' in self.file_type or 'document' in self.file_type:
                return 'fa-file-word'
            elif 'excel' in self.file_type or 'spreadsheet' in self.file_type:
                return 'fa-file-excel'
            elif 'powerpoint' in self.file_type or 'presentation' in self.file_type:
                return 'fa-file-powerpoint'
            elif 'zip' in self.file_type or 'rar' in self.file_type or 'compressed' in self.file_type:
                return 'fa-file-archive'
            elif 'text' in self.file_type:
                return 'fa-file-alt'
        return 'fa-file'

    def get_size_display(self):
        """عرض حجم الملف بشكل مقروء"""
        if not self.file_size:
            return '0 KB'

        size = self.file_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size/(1024*1024):.1f} MB"
        else:
            return f"{size/(1024*1024*1024):.1f} GB"

    def is_viewable_in_browser(self):
        """تحديد ما إذا كان الملف يمكن عرضه مباشرة في المتصفح"""
        viewable_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/svg+xml',
            'application/pdf', 'text/plain', 'text/html',
            'video/mp4', 'audio/mpeg'
        ]
        return self.file_type in viewable_types

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form

        user = User.query.filter_by(username=username).first()

        # تسجيل محاولة تسجيل الدخول
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')

        if user and user.check_password(password):
            if user.is_active:
                # تسجيل دخول ناجح
                login_log = UserLoginLog(
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='success'
                )
                db.session.add(login_log)
                db.session.commit()

                login_user(user, remember=remember)
                flash('تم تسجيل الدخول بنجاح', 'success')
                next_page = request.args.get('next')
                return redirect(next_page if next_page else url_for('dashboard'))
            else:
                # تسجيل محاولة دخول لحساب غير مفعل
                if user:
                    login_log = UserLoginLog(
                        user_id=user.id,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        status='inactive'
                    )
                    db.session.add(login_log)
                    db.session.commit()

                flash('الحساب غير مفعل', 'danger')
        else:
            # تسجيل محاولة دخول فاشلة
            if user:
                login_log = UserLoginLog(
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    status='failed'
                )
                db.session.add(login_log)
                db.session.commit()

            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'danger')

    # إضافة متغير التاريخ الحالي
    now = datetime.now()
    return render_template('login.html', now=now)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # الحصول على إحصائيات الرسائل

    # الرسائل المستلمة (الإصدار القديم)
    legacy_messages_count = Message.query.filter_by(recipient_id=current_user.id).count()
    legacy_inbox_count = Message.query.filter_by(recipient_id=current_user.id, is_archived=False).count()
    legacy_archived_count = Message.query.filter_by(recipient_id=current_user.id, is_archived=True).count()

    # الرسائل المستلمة (الإصدار الجديد - متعدد المستلمين)
    multi_recipient_ids = db.session.query(MessageRecipient.message_id)\
        .filter_by(recipient_id=current_user.id)\
        .all()
    multi_recipient_ids = [r[0] for r in multi_recipient_ids]

    multi_messages_count = len(multi_recipient_ids)

    # الرسائل غير المؤرشفة (الإصدار الجديد)
    multi_inbox_count = db.session.query(MessageRecipient)\
        .filter_by(recipient_id=current_user.id, is_archived=False)\
        .count()

    # الرسائل المؤرشفة (الإصدار الجديد)
    multi_archived_count = db.session.query(MessageRecipient)\
        .filter_by(recipient_id=current_user.id, is_archived=True)\
        .count()

    # الرسائل المرسلة
    sent_messages_count = Message.query.filter_by(sender_id=current_user.id).count()

    # إجمالي الإحصائيات
    stats = {
        'total_messages': legacy_messages_count + multi_messages_count,
        'inbox_messages': legacy_inbox_count + multi_inbox_count,
        'sent_messages': sent_messages_count,
        'archived_messages': legacy_archived_count + multi_archived_count
    }

    # الحصول على الرسائل الحديثة

    # الرسائل الحديثة (الإصدار القديم)
    legacy_recent_messages = Message.query.filter_by(
        recipient_id=current_user.id,
        is_archived=False
    ).order_by(Message.date.desc()).limit(5).all()

    # الرسائل الحديثة (الإصدار الجديد - متعدد المستلمين)
    multi_recipient_messages_ids = db.session.query(MessageRecipient.message_id)\
        .filter_by(recipient_id=current_user.id, is_archived=False)\
        .join(Message, Message.id == MessageRecipient.message_id)\
        .order_by(Message.date.desc())\
        .limit(5)\
        .all()

    multi_recipient_messages_ids = [r[0] for r in multi_recipient_messages_ids]
    multi_recent_messages = Message.query.filter(Message.id.in_(multi_recipient_messages_ids))\
        .order_by(Message.date.desc())\
        .all()

    # دمج الرسائل وترتيبها حسب التاريخ
    all_recent_messages = legacy_recent_messages + multi_recent_messages
    all_recent_messages.sort(key=lambda x: x.date, reverse=True)
    recent_messages = all_recent_messages[:5]  # أخذ أحدث 5 رسائل فقط

    # إضافة معلومات الحالة للرسائل
    for message in recent_messages:
        if message.is_multi_recipient:
            # الحصول على حالة الرسالة للمستخدم الحالي
            recipient_data = MessageRecipient.query.filter_by(
                message_id=message.id,
                recipient_id=current_user.id
            ).first()

            if recipient_data:
                message.status_color = recipient_data.get_status_color()
                message.status_text = recipient_data.get_status_display()
            else:
                message.status_color = 'secondary'
                message.status_text = 'غير معروف'
        else:
            message.status_color = message.get_status_color()
            message.status_text = message.get_status_display()

    return render_template('dashboard.html', stats=stats, recent_messages=recent_messages)

@app.route('/inbox')
@login_required
def inbox():
    # الرسائل من الإصدار القديم
    legacy_messages = Message.query.filter_by(
        recipient_id=current_user.id,
        is_archived=False
    ).order_by(Message.date.desc()).all()

    # الرسائل من الإصدار الجديد (متعدد المستلمين)
    multi_recipient_messages_ids = db.session.query(MessageRecipient.message_id)\
        .filter_by(recipient_id=current_user.id, is_archived=False)\
        .all()

    multi_recipient_messages_ids = [r[0] for r in multi_recipient_messages_ids]
    multi_recipient_messages = Message.query.filter(Message.id.in_(multi_recipient_messages_ids))\
        .order_by(Message.date.desc())\
        .all()

    # دمج الرسائل وترتيبها حسب التاريخ
    all_messages = legacy_messages + multi_recipient_messages
    all_messages.sort(key=lambda x: x.date, reverse=True)

    # إضافة معلومات الحالة للرسائل
    for message in all_messages:
        if message.is_multi_recipient:
            # الحصول على حالة الرسالة للمستخدم الحالي
            recipient_data = MessageRecipient.query.filter_by(
                message_id=message.id,
                recipient_id=current_user.id
            ).first()

            if recipient_data:
                message.status_color = recipient_data.get_status_color()
                message.status_text = recipient_data.get_status_display()
                message.recipient_status = recipient_data.status
            else:
                message.status_color = 'secondary'
                message.status_text = 'غير معروف'
                message.recipient_status = 'unknown'
        else:
            message.status_color = message.get_status_color()
            message.status_text = message.get_status_display()
            message.recipient_status = message.status

    return render_template('inbox.html', messages=all_messages)

@app.route('/outbox')
@login_required
def outbox():
    # الحصول على جميع الرسائل المرسلة
    messages = Message.query.filter_by(
        sender_id=current_user.id
    ).order_by(Message.date.desc()).all()

    # إضافة معلومات المستلمين للرسائل متعددة المستلمين
    for message in messages:
        if message.is_multi_recipient:
            # الحصول على عدد المستلمين
            recipients_count = MessageRecipient.query.filter_by(
                message_id=message.id
            ).count()

            # الحصول على عدد المستلمين الذين قرأوا الرسالة
            read_count = MessageRecipient.query.filter(
                MessageRecipient.message_id == message.id,
                MessageRecipient.status.in_(['read', 'replied', 'processing', 'completed', 'closed'])
            ).count()

            # إضافة المعلومات إلى الرسالة
            message.recipients_count = recipients_count
            message.read_count = read_count

            # الحصول على قائمة المستلمين
            recipients_data = MessageRecipient.query.filter_by(
                message_id=message.id
            ).all()

            recipients_list = []
            for r_data in recipients_data:
                recipient = User.query.get(r_data.recipient_id)
                if recipient:
                    recipients_list.append({
                        'username': recipient.username,
                        'status': r_data.status,
                        'status_display': r_data.get_status_display(),
                        'status_color': r_data.get_status_color()
                    })

            message.recipients_list = recipients_list

    return render_template('outbox.html', messages=messages)

@app.route('/archive')
@login_required
def archive():
    # الرسائل من الإصدار القديم
    legacy_messages = Message.query.filter_by(
        recipient_id=current_user.id,
        is_archived=True
    ).order_by(Message.date.desc()).all()

    # الرسائل من الإصدار الجديد (متعدد المستلمين)
    multi_recipient_messages_ids = db.session.query(MessageRecipient.message_id)\
        .filter_by(recipient_id=current_user.id, is_archived=True)\
        .all()

    multi_recipient_messages_ids = [r[0] for r in multi_recipient_messages_ids]
    multi_recipient_messages = Message.query.filter(Message.id.in_(multi_recipient_messages_ids))\
        .order_by(Message.date.desc())\
        .all()

    # دمج الرسائل وترتيبها حسب التاريخ
    all_messages = legacy_messages + multi_recipient_messages
    all_messages.sort(key=lambda x: x.date, reverse=True)

    # إضافة معلومات الحالة للرسائل
    for message in all_messages:
        if message.is_multi_recipient:
            # الحصول على حالة الرسالة للمستخدم الحالي
            recipient_data = MessageRecipient.query.filter_by(
                message_id=message.id,
                recipient_id=current_user.id
            ).first()

            if recipient_data:
                message.status_color = recipient_data.get_status_color()
                message.status_text = recipient_data.get_status_display()
                message.recipient_status = recipient_data.status
            else:
                message.status_color = 'secondary'
                message.status_text = 'غير معروف'
                message.recipient_status = 'unknown'
        else:
            message.status_color = message.get_status_color()
            message.status_text = message.get_status_display()
            message.recipient_status = message.status

    return render_template('archive.html', messages=all_messages)

@app.route('/users')
@login_required
def users():
    if not current_user.has_permission('manage_users'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    users = User.query.all()
    departments = Department.query.all()
    roles = Role.query.all()

    return render_template('users.html', users=users, departments=departments, roles=roles)

@app.route('/users/<int:id>/edit', methods=['POST'])
@login_required
def edit_user(id):
    if not current_user.has_permission('manage_users'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(id)

    if request.method == 'POST':
        email = request.form.get('email')
        department_id = request.form.get('department_id')
        position = request.form.get('position')
        role_id = request.form.get('role_id')
        role = request.form.get('role')
        password = request.form.get('password')

        # التحقق من عدم وجود مستخدم آخر بنفس البريد الإلكتروني
        existing_user = User.query.filter(User.email == email, User.id != id).first()
        if existing_user:
            flash('البريد الإلكتروني موجود بالفعل', 'danger')
            return redirect(url_for('users'))

        # تحديث بيانات المستخدم
        user.email = email
        user.position = position
        user.role_id = role_id
        user.role = role  # للتوافق مع الإصدارات السابقة

        # تحديث القسم
        if department_id:
            department = Department.query.get(department_id)
            if department:
                user.department_id = department_id
                user.department_name = department.name  # للتوافق مع الإصدارات السابقة
        else:
            user.department_id = None
            user.department_name = None

        # تحديث كلمة المرور إذا تم تقديمها
        if password and password.strip():
            user.set_password(password)

        try:
            db.session.commit()
            flash('تم تحديث المستخدم بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث المستخدم: {str(e)}', 'danger')

        return redirect(url_for('users'))

@app.route('/users/add', methods=['POST'])
@login_required
def add_user():
    if not current_user.has_permission('manage_users'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        department_id = request.form.get('department_id')
        position = request.form.get('position')
        role = request.form.get('role')

        # الحصول على اسم القسم إذا تم تحديد قسم
        department_name = None
        if department_id:
            department = Department.query.get(department_id)
            if department:
                department_name = department.name

        # التحقق من عدم وجود مستخدم بنفس اسم المستخدم أو البريد الإلكتروني
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            if existing_user.username == username:
                flash('اسم المستخدم موجود بالفعل', 'danger')
            else:
                flash('البريد الإلكتروني موجود بالفعل', 'danger')
            return redirect(url_for('users'))

        # الحصول على الدور
        role_id = request.form.get('role_id')

        # إنشاء مستخدم جديد
        new_user = User(
            username=username,
            email=email,
            department_id=department_id,
            department_name=department_name,  # للتوافق مع الإصدارات السابقة
            position=position,
            role=role,  # للتوافق مع الإصدارات السابقة
            role_id=role_id,
            is_active=True
        )
        new_user.password = generate_password_hash(password)

        # إضافة صلاحيات إدارة الحالة للمشرفين (للتوافق مع الإصدارات السابقة)
        if role == 'admin':
            new_user.can_change_status = True
            new_user.can_manage_status_permissions = True

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('تم إضافة المستخدم بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إضافة المستخدم: {str(e)}', 'danger')

        return redirect(url_for('users'))

@app.route('/users/<int:id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(id):
    if not current_user.has_permission('manage_users'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(id)

    # لا يمكن تعطيل حساب المستخدم الحالي
    if user.id == current_user.id:
        flash('لا يمكن تعطيل حسابك الشخصي', 'danger')
        return redirect(url_for('users'))

    # تغيير حالة المستخدم
    user.is_active = not user.is_active
    status_text = 'تفعيل' if user.is_active else 'تعطيل'

    try:
        db.session.commit()
        flash(f'تم {status_text} المستخدم بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء تغيير حالة المستخدم: {str(e)}', 'danger')

    return redirect(url_for('users'))

@app.route('/users/<int:id>/delete', methods=['POST'])
@login_required
def delete_user(id):
    if not current_user.has_permission('manage_users'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(id)

    # لا يمكن حذف حساب المستخدم الحالي
    if user.id == current_user.id:
        flash('لا يمكن حذف حسابك الشخصي', 'danger')
        return redirect(url_for('users'))

    try:
        db.session.delete(user)
        db.session.commit()
        flash('تم حذف المستخدم بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف المستخدم: {str(e)}', 'danger')

    return redirect(url_for('users'))

@app.route('/departments')
@login_required
def departments():
    if not current_user.has_permission('manage_departments'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    # الحصول على قائمة الأقسام
    departments = Department.query.all()

    return render_template('departments.html', departments=departments)

@app.route('/departments/add', methods=['POST'])
@login_required
def add_department():
    if not current_user.has_permission('manage_departments'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        # التحقق من عدم وجود قسم بنفس الاسم
        existing_department = Department.query.filter_by(name=name).first()
        if existing_department:
            flash('يوجد قسم بهذا الاسم بالفعل', 'danger')
            return redirect(url_for('departments'))

        # إنشاء قسم جديد
        new_department = Department(
            name=name,
            description=description,
            is_active=True
        )

        try:
            db.session.add(new_department)
            db.session.commit()
            flash('تم إضافة القسم بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إضافة القسم: {str(e)}', 'danger')

        return redirect(url_for('departments'))

@app.route('/departments/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_department(id):
    if current_user.role != 'admin':
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    department = Department.query.get_or_404(id)

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        # التحقق من عدم وجود قسم آخر بنفس الاسم
        existing_department = Department.query.filter(Department.name == name, Department.id != id).first()
        if existing_department:
            flash('يوجد قسم آخر بهذا الاسم بالفعل', 'danger')
            return redirect(url_for('edit_department', id=id))

        # تحديث بيانات القسم
        department.name = name
        department.description = description

        try:
            db.session.commit()
            flash('تم تحديث القسم بنجاح', 'success')
            return redirect(url_for('departments'))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث القسم: {str(e)}', 'danger')

    return render_template('edit_department.html', department=department)

@app.route('/departments/<int:id>/toggle-status', methods=['POST'])
@login_required
def toggle_department_status(id):
    if current_user.role != 'admin':
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    department = Department.query.get_or_404(id)

    # تغيير حالة القسم
    department.is_active = not department.is_active
    status_text = 'تفعيل' if department.is_active else 'تعطيل'

    try:
        db.session.commit()
        flash(f'تم {status_text} القسم بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء تغيير حالة القسم: {str(e)}', 'danger')

    return redirect(url_for('departments'))

@app.route('/departments/<int:id>/delete', methods=['POST'])
@login_required
def delete_department(id):
    if current_user.role != 'admin':
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    department = Department.query.get_or_404(id)

    # التحقق من عدم وجود مستخدمين في القسم
    if department.get_users_count() > 0:
        flash('لا يمكن حذف القسم لأنه يحتوي على مستخدمين', 'danger')
        return redirect(url_for('departments'))

    try:
        db.session.delete(department)
        db.session.commit()
        flash('تم حذف القسم بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف القسم: {str(e)}', 'danger')

    return redirect(url_for('departments'))

@app.route('/permissions')
@login_required
def permissions():
    if not current_user.has_permission('view_permissions'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    # الحصول على مجموعات الصلاحيات مرتبة حسب الترتيب
    permission_groups = PermissionGroup.query.order_by(PermissionGroup.order).all()

    return render_template('permissions.html', permission_groups=permission_groups)

@app.route('/roles')
@login_required
def roles():
    if not current_user.has_permission('manage_roles'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    roles = Role.query.all()
    permissions = Permission.query.all()

    return render_template('roles.html', roles=roles, permissions=permissions)

@app.route('/roles/add', methods=['POST'])
@login_required
def add_role():
    if not current_user.has_permission('manage_roles'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        # التحقق من عدم وجود دور بنفس الاسم
        existing_role = Role.query.filter_by(name=name).first()
        if existing_role:
            flash('يوجد دور بهذا الاسم بالفعل', 'danger')
            return redirect(url_for('roles'))

        # إنشاء دور جديد
        new_role = Role(
            name=name,
            description=description,
            is_system=False
        )

        # إضافة الصلاحيات المحددة
        permission_ids = request.form.getlist('permissions')
        if permission_ids:
            permissions = Permission.query.filter(Permission.id.in_(permission_ids)).all()
            new_role.permissions = permissions

        try:
            db.session.add(new_role)
            db.session.commit()
            flash('تم إضافة الدور بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إضافة الدور: {str(e)}', 'danger')

        return redirect(url_for('roles'))

@app.route('/roles/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_role(id):
    if not current_user.has_permission('manage_roles'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    role = Role.query.get_or_404(id)

    # لا يمكن تعديل الأدوار النظامية
    if role.is_system:
        flash('لا يمكن تعديل الأدوار النظامية', 'danger')
        return redirect(url_for('roles'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')

        # التحقق من عدم وجود دور آخر بنفس الاسم
        existing_role = Role.query.filter(Role.name == name, Role.id != id).first()
        if existing_role:
            flash('يوجد دور آخر بهذا الاسم بالفعل', 'danger')
            return redirect(url_for('edit_role', id=id))

        # تحديث بيانات الدور
        role.name = name
        role.description = description

        # تحديث الصلاحيات
        permission_ids = request.form.getlist('permissions')
        permissions = Permission.query.filter(Permission.id.in_(permission_ids)).all()
        role.permissions = permissions

        try:
            db.session.commit()
            flash('تم تحديث الدور بنجاح', 'success')
            return redirect(url_for('roles'))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث الدور: {str(e)}', 'danger')

    # الحصول على مجموعات الصلاحيات مرتبة حسب الترتيب
    permission_groups = PermissionGroup.query.order_by(PermissionGroup.order).all()

    # الحصول على الصلاحيات غير المصنفة
    uncategorized_permissions = Permission.query.filter_by(group_id=None).all()

    return render_template('edit_role.html',
                          role=role,
                          permission_groups=permission_groups,
                          uncategorized_permissions=uncategorized_permissions)

@app.route('/roles/<int:id>/delete', methods=['POST'])
@login_required
def delete_role(id):
    if not current_user.has_permission('manage_roles'):
        flash('غير مصرح بالوصول', 'danger')
        return redirect(url_for('dashboard'))

    role = Role.query.get_or_404(id)

    # لا يمكن حذف الأدوار النظامية
    if role.is_system:
        flash('لا يمكن حذف الأدوار النظامية', 'danger')
        return redirect(url_for('roles'))

    # التحقق من عدم وجود مستخدمين يستخدمون هذا الدور
    if role.users.count() > 0:
        flash('لا يمكن حذف الدور لأنه مستخدم من قبل مستخدمين', 'danger')
        return redirect(url_for('roles'))

    try:
        db.session.delete(role)
        db.session.commit()
        flash('تم حذف الدور بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف الدور: {str(e)}', 'danger')

    return redirect(url_for('roles'))

@app.route('/user-permissions')
@login_required
def user_permissions():
    # التحقق من صلاحية الوصول
    if not current_user.has_permission('manage_permissions'):
        flash('غير مصرح بالوصول لإدارة الصلاحيات', 'danger')
        return redirect(url_for('dashboard'))

    # الحصول على قائمة المستخدمين
    users = User.query.all()
    roles = Role.query.all()

    # الحصول على مجموعات الصلاحيات مرتبة حسب الترتيب
    permission_groups = PermissionGroup.query.order_by(PermissionGroup.order).all()

    # الحصول على سجل تغييرات الصلاحيات (آخر 10 تغييرات)
    recent_changes = PermissionChange.query.order_by(PermissionChange.change_date.desc()).limit(10).all()

    return render_template('user_permissions.html', users=users, roles=roles, permission_groups=permission_groups, recent_changes=recent_changes)

@app.route('/permission-changes')
@login_required
def permission_changes():
    # التحقق من صلاحية الوصول
    if not current_user.role == 'admin' and not current_user.has_status_management_permission():
        flash('غير مصرح بالوصول لسجل تغييرات الصلاحيات', 'danger')
        return redirect(url_for('dashboard'))

    # الحصول على جميع تغييرات الصلاحيات مرتبة حسب التاريخ (الأحدث أولاً)
    changes = PermissionChange.query.order_by(PermissionChange.change_date.desc()).all()

    return render_template('permission_changes.html', changes=changes)

@app.route('/users/<int:id>/permission-changes')
@login_required
def user_permission_changes(id):
    # التحقق من صلاحية الوصول
    if not current_user.role == 'admin' and not current_user.has_status_management_permission():
        flash('غير مصرح بالوصول لسجل تغييرات الصلاحيات', 'danger')
        return redirect(url_for('dashboard'))

    # الحصول على المستخدم
    user = User.query.get_or_404(id)

    # الحصول على تغييرات صلاحيات المستخدم
    changes = PermissionChange.query.filter_by(user_id=id).order_by(PermissionChange.change_date.desc()).all()

    return render_template('user_permission_changes.html', user=user, changes=changes)

@app.route('/login-logs')
@login_required
def login_logs():
    # التحقق من صلاحية الوصول
    if current_user.role != 'admin':
        flash('غير مصرح بالوصول لسجل دخول المستخدمين', 'danger')
        return redirect(url_for('dashboard'))

    # الحصول على سجل دخول جميع المستخدمين
    logs = UserLoginLog.query.order_by(UserLoginLog.login_date.desc()).limit(100).all()

    return render_template('user_login_logs.html', logs=logs)

@app.route('/users/<int:id>/login-logs')
@login_required
def user_login_logs(id):
    # التحقق من صلاحية الوصول
    if current_user.role != 'admin' and current_user.id != id:
        flash('غير مصرح بالوصول لسجل دخول المستخدم', 'danger')
        return redirect(url_for('dashboard'))

    # الحصول على المستخدم
    user = User.query.get_or_404(id)

    # الحصول على سجل دخول المستخدم
    logs = UserLoginLog.query.filter_by(user_id=id).order_by(UserLoginLog.login_date.desc()).all()

    return render_template('user_login_logs.html', user=user, logs=logs)

@app.route('/users/<int:id>/permissions', methods=['POST'])
@login_required
def update_user_permissions(id):
    # التحقق من صلاحية الوصول
    if not current_user.has_permission('manage_permissions'):
        return jsonify({'error': 'غير مصرح بالوصول لإدارة الصلاحيات'}), 403

    # الحصول على المستخدم
    user = User.query.get_or_404(id)

    # لا يمكن تعديل صلاحيات المشرفين
    if user.is_admin():
        return jsonify({'error': 'لا يمكن تعديل صلاحيات المشرف'}), 403

    # الحصول على البيانات من الطلب
    data = request.json
    notes = data.get('notes', '')  # ملاحظات اختيارية

    # تحديث الدور
    if 'role_id' in data:
        role_id = data.get('role_id')
        if role_id:
            role = Role.query.get(role_id)
            if role:
                old_role_id = user.role_id
                user.role_id = role_id

                # إنشاء سجل تغيير الدور
                permission_change = PermissionChange(
                    user_id=user.id,
                    changed_by_id=current_user.id,
                    permission_type='role_change',
                    old_value=str(old_role_id) if old_role_id else 'None',
                    new_value=str(role_id),
                    notes=notes,
                    role_id=role_id
                )

                db.session.add(permission_change)
                db.session.commit()

                return jsonify({
                    'message': 'تم تحديث دور المستخدم بنجاح',
                    'change_id': permission_change.id
                })

    # إضافة صلاحية مباشرة للمستخدم
    if 'permission_id' in data:
        permission_id = data.get('permission_id')
        if permission_id:
            permission = Permission.query.get(permission_id)
            if permission:
                # إنشاء سجل إضافة الصلاحية
                permission_change = PermissionChange(
                    user_id=user.id,
                    changed_by_id=current_user.id,
                    permission_type='permission_add',
                    old_value='false',
                    new_value='true',
                    notes=notes,
                    permission_id=permission_id
                )

                db.session.add(permission_change)
                db.session.commit()

                return jsonify({
                    'message': f'تم إضافة صلاحية {permission.get_display_name()} للمستخدم بنجاح',
                    'change_id': permission_change.id
                })

    # للتوافق مع الإصدارات السابقة - تحديث الصلاحيات المباشرة
    permission_type = data.get('permission_type')
    value = data.get('value')

    # التحقق من صحة البيانات
    if permission_type not in ['change_status', 'manage_permissions']:
        return jsonify({'error': 'نوع صلاحية غير صالح'}), 400

    # تحديث الصلاحيات وتسجيل التغيير
    try:
        # حفظ القيمة القديمة قبل التغيير
        if permission_type == 'change_status':
            old_value = user.can_change_status
            user.can_change_status = value
        elif permission_type == 'manage_permissions':
            old_value = user.can_manage_status_permissions
            user.can_manage_status_permissions = value

        # إنشاء سجل تغيير الصلاحية
        permission_change = PermissionChange(
            user_id=user.id,
            changed_by_id=current_user.id,
            permission_type=permission_type,
            old_value=old_value,
            new_value=value,
            notes=notes
        )

        # إضافة سجل التغيير وحفظ التغييرات
        db.session.add(permission_change)
        db.session.commit()

        return jsonify({
            'message': 'تم تحديث الصلاحيات بنجاح',
            'change_id': permission_change.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء تحديث الصلاحيات: {str(e)}'}), 500

@app.route('/message/<int:id>')
@login_required
def view_message(id):
    message = Message.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    has_access = False

    # المرسل دائمًا لديه حق الوصول
    if message.sender_id == current_user.id:
        has_access = True

    # للتوافق مع الإصدارات السابقة (رسالة بمستلم واحد)
    elif message.recipient_id == current_user.id:
        has_access = True

        # تحديث حالة الرسالة إذا كانت جديدة
        if message.status == 'new':
            message.change_status('read', current_user.id, 'تم قراءة الرسالة')
            db.session.commit()

    # التحقق من المستلمين المتعددين
    elif message.is_multi_recipient:
        # البحث عن المستخدم في قائمة المستلمين
        recipient_data = MessageRecipient.query.filter_by(
            message_id=message.id,
            recipient_id=current_user.id
        ).first()

        if recipient_data:
            has_access = True

            # تحديث حالة الرسالة إذا كانت جديدة
            if recipient_data.status == 'new':
                message.change_status('read', current_user.id, 'تم قراءة الرسالة', current_user.id)

                # تحديث تاريخ القراءة
                recipient_data.read_at = datetime.now()
                db.session.commit()

    if not has_access:
        flash('غير مصرح بالوصول إلى هذه الرسالة', 'danger')
        return redirect(url_for('inbox'))

    # إضافة متغير التاريخ الحالي لحساب الأيام المتبقية للاستحقاق
    now = datetime.now()

    # الحصول على معلومات المستلمين إذا كانت الرسالة متعددة المستلمين
    recipients_info = None
    if message.is_multi_recipient:
        recipients_data = MessageRecipient.query.filter_by(message_id=message.id).all()
        recipients_info = []

        for r_data in recipients_data:
            recipient = User.query.get(r_data.recipient_id)
            if recipient:
                recipients_info.append({
                    'id': recipient.id,
                    'username': recipient.username,
                    'full_name': recipient.full_name or recipient.username,
                    'department': recipient.department_name,
                    'status': r_data.status,
                    'status_display': r_data.get_status_display(),
                    'status_color': r_data.get_status_color(),
                    'read_at': r_data.read_at
                })

    return render_template('view_message.html', message=message, now=now, recipients_info=recipients_info)

@app.route('/message/create', methods=['GET', 'POST'])
@login_required
def create_message():
    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')
        include_signature = 'include_signature' in request.form
        recipient_type = request.form.get('recipient_type', 'user')

        # الحقول الجديدة
        priority = request.form.get('priority', 'normal')
        message_type = request.form.get('message_type')
        confidentiality = request.form.get('confidentiality', 'normal')
        reference_number = request.form.get('reference_number')
        due_date_str = request.form.get('due_date')

        # تحويل تاريخ الاستحقاق إلى كائن تاريخ إذا تم توفيره
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('صيغة تاريخ الاستحقاق غير صحيحة', 'danger')
                return redirect(url_for('create_message'))

        # إضافة التوقيع النصي إلى المحتوى إذا كان مطلوبًا
        if include_signature and current_user.signature:
            content = content + "\n\n--\n" + current_user.signature

        # إضافة صورة التوقيع إذا كان مطلوبًا
        include_signature_image = 'include_signature_image' in request.form
        has_signature_image = include_signature_image and current_user.signature_image

        # إنشاء الرسالة الأساسية
        message = Message(
            subject=subject,
            content=content,
            sender_id=current_user.id,
            priority=priority,
            message_type=message_type,
            confidentiality=confidentiality,
            reference_number=reference_number,
            due_date=due_date,
            recipient_type=recipient_type,
            is_multi_recipient=(recipient_type != 'user')
        )

        # معالجة المستلمين حسب النوع
        recipients = []

        if recipient_type == 'user':
            # مستلم فردي
            recipient_username = request.form.get('recipient')
            recipient = User.query.filter_by(username=recipient_username).first()

            if not recipient:
                flash('المستلم غير موجود', 'danger')
                return redirect(url_for('create_message'))

            # تعيين المستلم للتوافق مع الإصدارات السابقة
            message.recipient_id = recipient.id
            recipients.append(recipient)

        elif recipient_type == 'group':
            # مجموعة
            group_id = request.form.get('group_id')

            if not group_id:
                flash('يرجى اختيار مجموعة', 'danger')
                return redirect(url_for('create_message'))

            group = UserGroup.query.get(group_id)

            if not group:
                flash('المجموعة غير موجودة', 'danger')
                return redirect(url_for('create_message'))

            # الحصول على أعضاء المجموعة
            group_members = group.get_members()

            if not group_members:
                flash('المجموعة لا تحتوي على أعضاء', 'warning')
                return redirect(url_for('create_message'))

            # إضافة أعضاء المجموعة كمستلمين
            for member in group_members:
                # تجاهل المرسل نفسه
                if member.id != current_user.id:
                    recipients.append(member)

        elif recipient_type == 'multiple':
            # مستلمين متعددين
            multiple_recipients = request.form.getlist('multiple_recipients[]')

            if not multiple_recipients:
                flash('يرجى اختيار مستلم واحد على الأقل', 'danger')
                return redirect(url_for('create_message'))

            # إضافة المستلمين المحددين
            for user_id in multiple_recipients:
                user = User.query.get(user_id)
                if user and user.id != current_user.id:
                    recipients.append(user)

        # التحقق من وجود مستلمين
        if not recipients:
            flash('لم يتم تحديد أي مستلمين صالحين', 'danger')
            return redirect(url_for('create_message'))

        # معالجة الملفات المرفقة
        files = request.files.getlist('attachments')
        has_attachments = False

        for file in files:
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash(f'نوع الملف {file.filename} غير مسموح به', 'danger')
                    continue

                attachment = save_attachment(file)
                if attachment:
                    has_attachments = True
                    message.attachments.append(attachment)

        message.has_attachments = has_attachments
        db.session.add(message)
        db.session.commit()

        # إضافة المستلمين إلى الرسالة
        for recipient in recipients:
            message_recipient = MessageRecipient(
                message_id=message.id,
                recipient_id=recipient.id,
                recipient_type=recipient_type,
                status='new'
            )
            db.session.add(message_recipient)

            # إنشاء إشعار للمستلم
            if recipient.notifications_enabled:
                # تخصيص الإشعار حسب أولوية الرسالة
                icon = 'fa-envelope'
                color = 'primary'

                if priority == 'urgent':
                    icon = 'fa-exclamation-circle'
                    color = 'warning'
                    title = 'رسالة عاجلة'
                elif priority == 'very_urgent':
                    icon = 'fa-exclamation-triangle'
                    color = 'danger'
                    title = 'رسالة هامة جداً'
                else:
                    title = 'رسالة جديدة'

                create_notification(
                    recipient.id,
                    title,
                    f'لديك رسالة جديدة من {current_user.username}: {subject}',
                    icon,
                    color,
                    url_for('view_message', id=message.id)
                )

        db.session.commit()
        flash(f'تم إرسال الرسالة بنجاح إلى {len(recipients)} مستلم', 'success')
        return redirect(url_for('outbox'))

    # الحصول على البيانات اللازمة لصفحة إنشاء الرسالة
    users = User.query.filter(User.id != current_user.id).all()
    groups = UserGroup.query.filter(
        (UserGroup.is_public == True) |
        (UserGroup.created_by_id == current_user.id) |
        (UserGroup.id.in_([m.group_id for m in current_user.group_memberships]))
    ).all()
    favorites = FavoriteUser.query.filter_by(user_id=current_user.id).all()

    return render_template('create_message.html', users=users, groups=groups, favorites=favorites)

@app.route('/message/<int:id>/archive', methods=['POST'])
@login_required
def archive_message(id):
    message = Message.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    has_access = False

    # للتوافق مع الإصدارات السابقة (رسالة بمستلم واحد)
    if message.recipient_id == current_user.id:
        has_access = True

        # تحديث حالة الأرشفة
        message.is_archived = True
        db.session.commit()

    # التحقق من المستلمين المتعددين
    elif message.is_multi_recipient:
        # البحث عن المستخدم في قائمة المستلمين
        recipient_data = MessageRecipient.query.filter_by(
            message_id=message.id,
            recipient_id=current_user.id
        ).first()

        if recipient_data:
            has_access = True

            # تحديث حالة الأرشفة
            recipient_data.is_archived = True
            db.session.commit()

    if not has_access:
        return jsonify({'error': 'غير مصرح بالوصول'}), 403

    return jsonify({'message': 'تم الأرشفة بنجاح'})

@app.route('/message/<int:id>/delete', methods=['POST'])
@login_required
def delete_message(id):
    message = Message.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        return jsonify({'error': 'غير مصرح بالوصول'}), 403

    # التحقق من صلاحية حذف الرسائل
    if not current_user.has_permission('delete_messages'):
        return jsonify({'error': 'ليس لديك صلاحية حذف الرسائل'}), 403

    try:
        db.session.delete(message)
        db.session.commit()
        return jsonify({'message': 'تم حذف الرسالة بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء حذف الرسالة: {str(e)}'}), 500

@app.route('/messages/delete-multiple', methods=['POST'])
@login_required
def delete_multiple_messages():
    # الحصول على قائمة معرفات الرسائل المراد حذفها
    message_ids = request.json.get('message_ids', [])

    if not message_ids:
        return jsonify({'error': 'لم يتم تحديد أي رسائل للحذف'}), 400

    # التحقق من صلاحية حذف الرسائل
    if not current_user.has_permission('delete_messages'):
        return jsonify({'error': 'ليس لديك صلاحية حذف الرسائل'}), 403

    # الحصول على الرسائل المحددة
    messages = Message.query.filter(Message.id.in_(message_ids)).all()

    # التحقق من صلاحية الوصول لكل رسالة
    for message in messages:
        if message.recipient_id != current_user.id and message.sender_id != current_user.id:
            return jsonify({'error': 'غير مصرح بالوصول لبعض الرسائل المحددة'}), 403

    try:
        # حذف الرسائل
        deleted_count = 0
        for message in messages:
            db.session.delete(message)
            deleted_count += 1

        db.session.commit()
        return jsonify({
            'message': f'تم حذف {deleted_count} رسالة بنجاح',
            'count': deleted_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء حذف الرسائل: {str(e)}'}), 500

@app.route('/message/<int:id>/change-status', methods=['POST'])
@login_required
def change_message_status(id):
    message = Message.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    has_access = False
    recipient_id = None

    # المرسل دائمًا لديه حق الوصول
    if message.sender_id == current_user.id:
        has_access = True

    # للتوافق مع الإصدارات السابقة (رسالة بمستلم واحد)
    elif message.recipient_id == current_user.id:
        has_access = True
        recipient_id = current_user.id

    # التحقق من المستلمين المتعددين
    elif message.is_multi_recipient:
        # البحث عن المستخدم في قائمة المستلمين
        recipient_data = MessageRecipient.query.filter_by(
            message_id=message.id,
            recipient_id=current_user.id
        ).first()

        if recipient_data:
            has_access = True
            recipient_id = current_user.id

    if not has_access:
        return jsonify({'error': 'غير مصرح بالوصول'}), 403

    # التحقق من صلاحية تغيير الحالة
    if not current_user.has_status_permission():
        # السماح للمستخدم بتغيير حالة الرسالة إلى "مقروء" فقط إذا كان هو المستلم
        if recipient_id and (
            (not message.is_multi_recipient and message.status == 'new') or
            (message.is_multi_recipient and recipient_data and recipient_data.status == 'new')
        ) and request.json.get('status') == 'read':
            pass  # السماح بهذا التغيير
        else:
            return jsonify({'error': 'ليس لديك صلاحية تغيير حالة الرسائل'}), 403

    # الحصول على البيانات من الطلب
    data = request.json
    new_status = data.get('status')
    notes = data.get('notes', '')

    # الحصول على recipient_id من الطلب إذا تم تحديده (للمشرفين)
    if data.get('recipient_id'):
        recipient_id = data.get('recipient_id')

    # التحقق من صحة الحالة الجديدة
    valid_statuses = ['new', 'read', 'replied', 'processing', 'completed', 'closed', 'postponed']
    if new_status not in valid_statuses:
        return jsonify({'error': 'حالة غير صالحة'}), 400

    # تغيير حالة الرسالة
    if message.change_status(new_status, current_user.id, notes, recipient_id):
        db.session.commit()

        # إنشاء إشعار للمرسل إذا كان المستخدم الحالي هو المستلم
        if recipient_id == current_user.id and message.sender_id != current_user.id:
            sender = User.query.get(message.sender_id)
            if sender and sender.notifications_enabled:
                status_text = message.get_status_display()
                create_notification(
                    sender.id,
                    'تغيير حالة الرسالة',
                    f'تم تغيير حالة رسالتك "{message.subject}" إلى "{status_text}"',
                    'fa-exchange-alt',
                    'warning',
                    url_for('view_message', id=message.id)
                )

        return jsonify({'message': 'تم تغيير الحالة بنجاح'})
    else:
        return jsonify({'message': 'لم يتم تغيير الحالة (الحالة الحالية هي نفسها)'})

@app.route('/message/<int:id>/status-history', methods=['GET'])
@login_required
def get_message_status_history(id):
    message = Message.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        return jsonify({'error': 'غير مصرح بالوصول'}), 403

    # الحصول على سجل تغييرات الحالة
    status_changes = MessageStatusChange.query.filter_by(message_id=id).order_by(MessageStatusChange.change_date.desc()).all()

    # تحويل البيانات إلى تنسيق JSON
    history = []
    for change in status_changes:
        history.append({
            'date': change.change_date.strftime('%Y-%m-%d %H:%M'),
            'old_status': change.old_status,
            'old_status_display': message.get_status_display() if change.old_status == message.status else change.old_status,
            'new_status': change.new_status,
            'new_status_display': message.get_status_display() if change.new_status == message.status else change.new_status,
            'changed_by': change.changed_by.username,
            'notes': change.notes or ''
        })

    return jsonify({'history': history})

@app.route('/api/message/<int:id>/recipients')
@login_required
def api_message_recipients(id):
    """واجهة برمجة التطبيقات للحصول على قائمة مستلمي الرسالة"""
    message = Message.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    if message.sender_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'غير مصرح بالوصول'}), 403

    # التحقق من أن الرسالة متعددة المستلمين
    if not message.is_multi_recipient:
        # للتوافق مع الإصدارات السابقة
        recipient = User.query.get(message.recipient_id) if message.recipient_id else None
        if recipient:
            recipients_data = [{
                'id': recipient.id,
                'username': recipient.username,
                'full_name': recipient.full_name or recipient.username,
                'department': recipient.department_name,
                'status': message.status,
                'status_display': message.get_status_display(),
                'status_color': message.get_status_color(),
                'read_at': message.read_at.strftime('%Y-%m-%d %H:%M') if message.read_at else None
            }]
        else:
            recipients_data = []
    else:
        # الحصول على قائمة المستلمين
        recipients = MessageRecipient.query.filter_by(message_id=id).all()

        recipients_data = []
        for recipient_data in recipients:
            recipient = User.query.get(recipient_data.recipient_id)
            if recipient:
                recipients_data.append({
                    'id': recipient.id,
                    'username': recipient.username,
                    'full_name': recipient.full_name or recipient.username,
                    'department': recipient.department_name,
                    'status': recipient_data.status,
                    'status_display': recipient_data.get_status_display(),
                    'status_color': recipient_data.get_status_color(),
                    'read_at': recipient_data.read_at.strftime('%Y-%m-%d %H:%M') if recipient_data.read_at else None
                })

    return jsonify({'recipients': recipients_data})

@app.route('/api/group/<int:id>/members')
@login_required
def api_group_members(id):
    """واجهة برمجة التطبيقات للحصول على قائمة أعضاء المجموعة"""
    group = UserGroup.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    if not group.is_public and group.created_by_id != current_user.id and not group.is_member(current_user.id) and not current_user.is_admin():
        return jsonify({'error': 'غير مصرح بالوصول'}), 403

    # الحصول على قائمة الأعضاء
    memberships = UserGroupMembership.query.filter_by(group_id=id).all()

    members_data = []
    for membership in memberships:
        member = User.query.get(membership.user_id)
        if member:
            members_data.append({
                'id': member.id,
                'username': member.username,
                'full_name': member.full_name or member.username,
                'department': member.department_name,
                'role': membership.role
            })

    return jsonify({'members': members_data})

@app.route('/api/user/favorite/add/<int:user_id>', methods=['POST'])
@login_required
def api_add_favorite_user(user_id):
    """واجهة برمجة التطبيقات لإضافة مستخدم إلى المفضلة"""
    # التحقق من وجود المستخدم
    user = User.query.get_or_404(user_id)

    # التحقق من عدم إضافة المستخدم لنفسه
    if user_id == current_user.id:
        return jsonify({'error': 'لا يمكن إضافة نفسك إلى المفضلة'}), 400

    # التحقق من عدم وجود المستخدم في المفضلة بالفعل
    existing = FavoriteUser.query.filter_by(
        user_id=current_user.id,
        favorite_user_id=user_id
    ).first()

    if existing:
        return jsonify({'error': 'المستخدم موجود بالفعل في المفضلة'}), 400

    # إضافة المستخدم إلى المفضلة
    favorite = FavoriteUser(
        user_id=current_user.id,
        favorite_user_id=user_id
    )

    try:
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تمت إضافة المستخدم إلى المفضلة بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء إضافة المستخدم إلى المفضلة: {str(e)}'}), 500

@app.route('/api/user/favorite/remove/<int:user_id>', methods=['POST'])
@login_required
def api_remove_favorite_user(user_id):
    """واجهة برمجة التطبيقات لإزالة مستخدم من المفضلة"""
    # البحث عن المستخدم في المفضلة
    favorite = FavoriteUser.query.filter_by(
        user_id=current_user.id,
        favorite_user_id=user_id
    ).first()

    if not favorite:
        return jsonify({'error': 'المستخدم غير موجود في المفضلة'}), 404

    try:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تمت إزالة المستخدم من المفضلة بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء إزالة المستخدم من المفضلة: {str(e)}'}), 500

@app.route('/message/<int:id>/reply', methods=['GET', 'POST'])
@login_required
def reply_message(id):
    original_message = Message.query.get_or_404(id)

    # التحقق من أن المستخدم هو المستلم للرسالة الأصلية
    if original_message.recipient_id != current_user.id:
        flash('غير مصرح بالوصول إلى هذه الرسالة', 'danger')
        return redirect(url_for('inbox'))

    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')
        include_signature = 'include_signature' in request.form

        # الحقول الجديدة
        priority = request.form.get('priority', original_message.priority or 'normal')
        message_type = request.form.get('message_type', original_message.message_type)
        confidentiality = request.form.get('confidentiality', original_message.confidentiality or 'normal')
        reference_number = request.form.get('reference_number')
        due_date_str = request.form.get('due_date')

        # تحويل تاريخ الاستحقاق إلى كائن تاريخ إذا تم توفيره
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('صيغة تاريخ الاستحقاق غير صحيحة', 'danger')

        # إضافة التوقيع النصي إلى المحتوى إذا كان مطلوبًا
        if include_signature and current_user.signature:
            content = content + "\n\n--\n" + current_user.signature

        # إضافة صورة التوقيع إذا كان مطلوبًا
        include_signature_image = 'include_signature_image' in request.form
        has_signature_image = include_signature_image and current_user.signature_image

        # إنشاء رسالة رد
        reply = Message(
            subject=subject,
            content=content,
            sender_id=current_user.id,
            recipient_id=original_message.sender_id,
            priority=priority,
            message_type=message_type,
            confidentiality=confidentiality,
            reference_number=reference_number,
            due_date=due_date
        )

        # معالجة الملفات المرفقة
        files = request.files.getlist('attachments')
        has_attachments = False

        for file in files:
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash(f'نوع الملف {file.filename} غير مسموح به', 'danger')
                    continue

                attachment = save_attachment(file)
                if attachment:
                    has_attachments = True
                    reply.attachments.append(attachment)

        reply.has_attachments = has_attachments

        # تحديث حالة الرسالة الأصلية
        original_message.change_status('replied', current_user.id, 'تم الرد على الرسالة')

        db.session.add(reply)
        db.session.commit()

        # إنشاء إشعار للمستلم
        recipient = User.query.get(reply.recipient_id)
        if recipient and recipient.notifications_enabled:
            # تخصيص الإشعار حسب أولوية الرسالة
            icon = 'fa-reply'
            color = 'info'

            if priority == 'urgent':
                icon = 'fa-exclamation-circle'
                color = 'warning'
                title = 'رد عاجل على رسالة'
            elif priority == 'very_urgent':
                icon = 'fa-exclamation-triangle'
                color = 'danger'
                title = 'رد هام جداً على رسالة'
            else:
                title = 'رد على رسالة'

            create_notification(
                recipient.id,
                title,
                f'لديك رد جديد من {current_user.username} على رسالتك: {original_message.subject}',
                icon,
                color,
                url_for('view_message', id=reply.id)
            )

        flash('تم إرسال الرد بنجاح', 'success')
        return redirect(url_for('inbox'))

    # تحضير موضوع الرد
    reply_subject = f"رد: {original_message.subject}"

    return render_template('reply_message.html',
                          original_message=original_message,
                          reply_subject=reply_subject)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            # إنشاء رمز عشوائي من 6 أرقام
            reset_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

            # تخزين الرمز وتاريخ انتهاء صلاحيته (10 دقائق)
            user.reset_token = reset_code
            user.reset_token_expiry = datetime.now() + timedelta(minutes=10)
            db.session.commit()

            # عرض الرمز مباشرة للمستخدم
            return render_template('reset_code.html', reset_code=reset_code, email=email)

        flash('لم يتم العثور على حساب بهذا البريد الإلكتروني', 'danger')

    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        reset_code = request.form.get('reset_code')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        user = User.query.filter_by(email=email, reset_token=reset_code).first()

        if user is None:
            flash('البريد الإلكتروني أو رمز إعادة التعيين غير صحيح', 'danger')
            return redirect(url_for('reset_password'))

        if user.reset_token_expiry < datetime.now():
            flash('انتهت صلاحية رمز إعادة التعيين. يرجى طلب رمز جديد', 'danger')
            return redirect(url_for('forgot_password'))

        if password != confirm_password:
            flash('كلمات المرور غير متطابقة', 'danger')
            return redirect(url_for('reset_password'))

        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()

        flash('تم تغيير كلمة المرور بنجاح', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

@app.route('/profile')
@login_required
def profile():
    # Get message statistics
    stats = {
        'total_messages': Message.query.filter_by(recipient_id=current_user.id).count(),
        'inbox_messages': Message.query.filter_by(recipient_id=current_user.id, is_archived=False).count(),
        'sent_messages': Message.query.filter_by(sender_id=current_user.id).count(),
        'archived_messages': Message.query.filter_by(recipient_id=current_user.id, is_archived=True).count()
    }

    return render_template('profile.html', stats=stats)

@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # التحقق من كلمة المرور الحالية
        current_password = request.form.get('current_password')
        if not current_user.check_password(current_password):
            flash('كلمة المرور الحالية غير صحيحة', 'danger')
            return redirect(url_for('edit_profile'))

        # تحديث البيانات الأساسية
        current_user.email = request.form.get('email')
        current_user.full_name = request.form.get('full_name')
        current_user.phone = request.form.get('phone')
        current_user.signature = request.form.get('signature')

        # تحديث القسم
        department_id = request.form.get('department_id')
        if department_id:
            department = Department.query.get(department_id)
            if department:
                current_user.department_id = department_id
                current_user.department_name = department.name  # للتوافق مع الإصدارات السابقة
        else:
            current_user.department_id = None
            current_user.department_name = None

        # تحديث المنصب
        current_user.position = request.form.get('position')
        current_user.bio = request.form.get('bio')

        # التحقق من تغيير كلمة المرور
        new_password = request.form.get('new_password')
        if new_password:
            confirm_password = request.form.get('confirm_password')
            if new_password != confirm_password:
                flash('كلمات المرور الجديدة غير متطابقة', 'danger')
                return redirect(url_for('edit_profile'))
            current_user.set_password(new_password)

        # معالجة صورة الملف الشخصي
        profile_image = request.files.get('profile_image')
        if profile_image and profile_image.filename:
            # التحقق من أن الملف هو صورة
            if not profile_image.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                flash('يجب أن تكون صورة الملف الشخصي بصيغة PNG أو JPG أو JPEG أو GIF', 'danger')
                return redirect(url_for('edit_profile'))

            # تأمين اسم الملف
            original_filename = secure_filename(profile_image.filename)

            # إنشاء اسم فريد للملف باستخدام UUID
            file_ext = os.path.splitext(original_filename)[1]
            unique_filename = f"profile_{current_user.id}_{uuid.uuid4().hex}{file_ext}"

            # تحديد مسار الملف
            profile_images_folder = os.path.join(app.static_folder, 'uploads/profile_images')

            # التأكد من وجود المجلد
            if not os.path.exists(profile_images_folder):
                os.makedirs(profile_images_folder)

            file_path = os.path.join(profile_images_folder, unique_filename)

            # حفظ الملف
            profile_image.save(file_path)

            # تحديث مسار الصورة في قاعدة البيانات
            current_user.profile_image = f'/static/uploads/profile_images/{unique_filename}'

        # معالجة صورة التوقيع
        signature_image = request.files.get('signature_image')
        if signature_image and signature_image.filename:
            # التحقق من أن الملف هو صورة
            if not signature_image.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                flash('يجب أن تكون صورة التوقيع بصيغة PNG أو JPG أو JPEG أو GIF', 'danger')
                return redirect(url_for('edit_profile'))

            # تأمين اسم الملف
            original_filename = secure_filename(signature_image.filename)

            # إنشاء اسم فريد للملف باستخدام UUID
            file_ext = os.path.splitext(original_filename)[1]
            unique_filename = f"signature_{current_user.id}_{uuid.uuid4().hex}{file_ext}"

            # تحديد مسار الملف
            signatures_folder = os.path.join(app.static_folder, 'uploads/signatures')

            # التأكد من وجود المجلد
            if not os.path.exists(signatures_folder):
                os.makedirs(signatures_folder)

            file_path = os.path.join(signatures_folder, unique_filename)

            # حفظ الملف
            signature_image.save(file_path)

            # تخزين مسار صورة التوقيع في حقل التوقيع
            current_user.signature_image = f'/static/uploads/signatures/{unique_filename}'

        db.session.commit()
        flash('تم تحديث الملف الشخصي بنجاح', 'success')
        return redirect(url_for('profile'))

    # الحصول على قائمة الأقسام
    departments = Department.query.all()

    return render_template('edit_profile.html', departments=departments)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # تحديث إعدادات النظام
        current_user.theme = request.form.get('theme')
        current_user.language = 'ar'  # تعيين اللغة العربية دائمًا
        current_user.notifications_enabled = 'notifications_enabled' in request.form

        db.session.commit()
        flash('تم حفظ الإعدادات بنجاح', 'success')
        return redirect(url_for('profile'))

    return render_template('settings.html')

@app.route('/favorites')
@login_required
def favorites():
    """صفحة إدارة المستخدمين المفضلين"""
    # الحصول على المستخدمين المفضلين
    favorites = FavoriteUser.query.filter_by(user_id=current_user.id).all()

    # الحصول على قائمة المستخدمين الآخرين (غير المفضلين)
    favorite_user_ids = [f.favorite_user_id for f in favorites]
    users = User.query.filter(
        User.id != current_user.id,
        ~User.id.in_(favorite_user_ids) if favorite_user_ids else True
    ).all()

    return render_template('favorites.html', favorites=favorites, users=users)

# وظائف إدارة الإشعارات
@app.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    per_page = 10

    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return render_template('notifications.html', notifications=notifications)

@app.route('/notifications/mark-read/<int:id>', methods=['POST'])
@login_required
def mark_notification_read(id):
    notification = Notification.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    if notification.user_id != current_user.id:
        return jsonify({'error': 'غير مصرح بالوصول'}), 403

    notification.is_read = True
    db.session.commit()

    return jsonify({'success': True})

@app.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()

    return jsonify({'success': True})

@app.route('/notifications/count')
@login_required
def get_notifications_count():
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})

@app.route('/api/notifications')
@login_required
def get_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .limit(5)\
        .all()

    result = []
    for notification in notifications:
        result.append({
            'id': notification.id,
            'title': notification.title,
            'content': notification.content,
            'icon': notification.icon,
            'color': notification.color,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_read': notification.is_read,
            'link': notification.link
        })

    return jsonify({'notifications': result})

@app.route('/api/group/<int:group_id>/members')
@login_required
def get_group_members(group_id):
    """الحصول على أعضاء المجموعة"""
    group = UserGroup.query.get_or_404(group_id)

    # التحقق من صلاحية الوصول (المجموعات العامة أو المجموعات التي ينتمي إليها المستخدم)
    if not group.is_public and not group.is_member(current_user.id):
        return jsonify({'error': 'غير مصرح بالوصول'}), 403

    members = group.get_members()
    result = []

    for member in members:
        result.append({
            'id': member.id,
            'username': member.username,
            'full_name': member.full_name,
            'department': member.department_name
        })

    return jsonify({'members': result})

@app.route('/api/user/favorites')
@login_required
def get_user_favorites():
    """الحصول على المستخدمين المفضلين"""
    favorites = FavoriteUser.query.filter_by(user_id=current_user.id).all()
    result = []

    for favorite in favorites:
        result.append({
            'id': favorite.favorite_user.id,
            'username': favorite.favorite_user.username,
            'full_name': favorite.favorite_user.full_name,
            'department': favorite.favorite_user.department_name
        })

    return jsonify({'favorites': result})

@app.route('/api/user/favorite/add/<int:user_id>', methods=['POST'])
@login_required
def add_favorite_user(user_id):
    """إضافة مستخدم إلى المفضلة"""
    # التحقق من وجود المستخدم
    user = User.query.get_or_404(user_id)

    # التحقق من عدم إضافة المستخدم نفسه
    if user_id == current_user.id:
        return jsonify({'error': 'لا يمكن إضافة نفسك إلى المفضلة'}), 400

    # التحقق من عدم وجود المستخدم بالفعل في المفضلة
    existing = FavoriteUser.query.filter_by(
        user_id=current_user.id,
        favorite_user_id=user_id
    ).first()

    if existing:
        return jsonify({'error': 'المستخدم موجود بالفعل في المفضلة'}), 400

    # إضافة المستخدم إلى المفضلة
    favorite = FavoriteUser(
        user_id=current_user.id,
        favorite_user_id=user_id
    )

    db.session.add(favorite)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'تمت إضافة {user.username} إلى المفضلة'
    })

@app.route('/api/user/favorite/remove/<int:user_id>', methods=['POST'])
@login_required
def remove_favorite_user(user_id):
    """إزالة مستخدم من المفضلة"""
    # التحقق من وجود المستخدم في المفضلة
    favorite = FavoriteUser.query.filter_by(
        user_id=current_user.id,
        favorite_user_id=user_id
    ).first_or_404()

    # حفظ اسم المستخدم قبل الحذف
    username = favorite.favorite_user.username

    # حذف المستخدم من المفضلة
    db.session.delete(favorite)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'تمت إزالة {username} من المفضلة'
    })


@app.route('/groups')
@login_required
def groups():
    """صفحة إدارة المجموعات"""
    # الحصول على المجموعات التي يمكن للمستخدم رؤيتها
    groups = UserGroup.query.filter(
        (UserGroup.is_public == True) |
        (UserGroup.created_by_id == current_user.id) |
        (UserGroup.id.in_([m.group_id for m in current_user.group_memberships]))
    ).order_by(UserGroup.name).all()

    # الحصول على قائمة المستخدمين لإضافتهم للمجموعات
    users = User.query.filter(User.id != current_user.id).all()

    return render_template('groups.html', groups=groups, users=users)

@app.route('/groups/add', methods=['POST'])
@login_required
def add_group():
    """إضافة مجموعة جديدة"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_public = 'is_public' in request.form

        # التحقق من عدم وجود مجموعة بنفس الاسم
        existing_group = UserGroup.query.filter_by(name=name).first()
        if existing_group:
            flash('يوجد مجموعة بهذا الاسم بالفعل', 'danger')
            return redirect(url_for('groups'))

        # إنشاء مجموعة جديدة
        new_group = UserGroup(
            name=name,
            description=description,
            created_by_id=current_user.id,
            is_public=is_public,
            is_active=True
        )

        try:
            db.session.add(new_group)
            db.session.commit()

            # إضافة المنشئ كمشرف في المجموعة
            membership = UserGroupMembership(
                group_id=new_group.id,
                user_id=current_user.id,
                role='admin'
            )
            db.session.add(membership)
            db.session.commit()

            flash('تم إنشاء المجموعة بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إنشاء المجموعة: {str(e)}', 'danger')

        return redirect(url_for('groups'))

@app.route('/groups/<int:id>/edit', methods=['POST'])
@login_required
def edit_group(id):
    """تعديل مجموعة"""
    group = UserGroup.query.get_or_404(id)

    # التحقق من صلاحية الوصول (المنشئ أو المشرف)
    if group.created_by_id != current_user.id and not group.is_admin(current_user.id) and not current_user.has_permission('manage_groups'):
        flash('غير مصرح بتعديل هذه المجموعة', 'danger')
        return redirect(url_for('groups'))

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_public = 'is_public' in request.form

        # التحقق من عدم وجود مجموعة أخرى بنفس الاسم
        existing_group = UserGroup.query.filter(UserGroup.name == name, UserGroup.id != id).first()
        if existing_group:
            flash('يوجد مجموعة أخرى بهذا الاسم بالفعل', 'danger')
            return redirect(url_for('groups'))

        # تحديث بيانات المجموعة
        group.name = name
        group.description = description
        group.is_public = is_public

        try:
            db.session.commit()
            flash('تم تحديث المجموعة بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء تحديث المجموعة: {str(e)}', 'danger')

        return redirect(url_for('groups'))

@app.route('/groups/<int:id>/delete', methods=['POST'])
@login_required
def delete_group(id):
    """حذف مجموعة"""
    group = UserGroup.query.get_or_404(id)

    # التحقق من صلاحية الوصول (المنشئ فقط أو مدير النظام)
    if group.created_by_id != current_user.id and not current_user.has_permission('manage_groups'):
        flash('غير مصرح بحذف هذه المجموعة', 'danger')
        return redirect(url_for('groups'))

    try:
        # حذف المجموعة (سيتم حذف العضويات تلقائيًا بسبب cascade)
        db.session.delete(group)
        db.session.commit()
        flash('تم حذف المجموعة بنجاح', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'حدث خطأ أثناء حذف المجموعة: {str(e)}', 'danger')

    return redirect(url_for('groups'))

@app.route('/groups/<int:group_id>/members/add', methods=['POST'])
@login_required
def add_group_member(group_id):
    """إضافة عضو إلى مجموعة"""
    group = UserGroup.query.get_or_404(group_id)

    # التحقق من صلاحية الوصول (المنشئ أو المشرف)
    if group.created_by_id != current_user.id and not group.is_admin(current_user.id) and not current_user.has_permission('manage_groups'):
        flash('غير مصرح بإضافة أعضاء لهذه المجموعة', 'danger')
        return redirect(url_for('groups'))

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        role = request.form.get('role', 'member')

        # التحقق من وجود المستخدم
        user = User.query.get(user_id)
        if not user:
            flash('المستخدم غير موجود', 'danger')
            return redirect(url_for('groups'))

        # التحقق من عدم وجود العضو بالفعل
        existing_membership = UserGroupMembership.query.filter_by(
            group_id=group_id,
            user_id=user_id
        ).first()

        if existing_membership:
            flash('المستخدم عضو بالفعل في هذه المجموعة', 'warning')
            return redirect(url_for('groups'))

        # إضافة العضو
        membership = UserGroupMembership(
            group_id=group_id,
            user_id=user_id,
            role=role
        )

        try:
            db.session.add(membership)
            db.session.commit()
            flash('تم إضافة العضو بنجاح', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ أثناء إضافة العضو: {str(e)}', 'danger')

        return redirect(url_for('groups'))

@app.route('/groups/<int:group_id>/members/<int:user_id>/remove', methods=['POST'])
@login_required
def remove_group_member(group_id, user_id):
    """إزالة عضو من مجموعة"""
    group = UserGroup.query.get_or_404(group_id)

    # التحقق من صلاحية الوصول (المنشئ أو المشرف)
    if group.created_by_id != current_user.id and not group.is_admin(current_user.id) and not current_user.has_permission('manage_groups'):
        return jsonify({'error': 'غير مصرح بإزالة أعضاء من هذه المجموعة'}), 403

    # التحقق من عدم إزالة المنشئ
    if user_id == group.created_by_id:
        return jsonify({'error': 'لا يمكن إزالة منشئ المجموعة'}), 400

    # البحث عن العضوية
    membership = UserGroupMembership.query.filter_by(
        group_id=group_id,
        user_id=user_id
    ).first()

    if not membership:
        return jsonify({'error': 'المستخدم ليس عضوًا في هذه المجموعة'}), 404

    try:
        db.session.delete(membership)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم إزالة العضو بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء إزالة العضو: {str(e)}'}), 500





# دالة مساعدة لإنشاء إشعار جديد
def create_notification(user_id, title, content, icon='fa-bell', color='primary', link=None):
    notification = Notification(
        user_id=user_id,
        title=title,
        content=content,
        icon=icon,
        color=color,
        link=link
    )
    db.session.add(notification)
    db.session.commit()
    return notification

@app.route('/attachments/<int:id>/download')
@login_required
def download_attachment(id):
    """تنزيل الملف المرفق"""
    attachment = Attachment.query.get_or_404(id)
    message = Message.query.get(attachment.message_id)

    # التحقق من صلاحية الوصول
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        abort(403)  # غير مصرح بالوصول

    # استخراج اسم الملف من المسار الكامل
    directory = os.path.dirname(attachment.file_path)
    filename = os.path.basename(attachment.file_path)

    # إرسال الملف للتنزيل
    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name=attachment.original_filename
    )

@app.route('/attachments/<int:id>/view')
@login_required
def view_attachment(id):
    """عرض الملف المرفق مباشرة في المتصفح"""
    attachment = Attachment.query.get_or_404(id)
    message = Message.query.get(attachment.message_id)

    # التحقق من صلاحية الوصول
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        abort(403)  # غير مصرح بالوصول

    # التحقق من إمكانية عرض الملف في المتصفح
    if not attachment.is_viewable_in_browser():
        return redirect(url_for('download_attachment', id=id))

    # استخراج اسم الملف من المسار الكامل
    directory = os.path.dirname(attachment.file_path)
    filename = os.path.basename(attachment.file_path)

    # إرسال الملف للعرض
    return send_from_directory(
        directory,
        filename,
        as_attachment=False,
        mimetype=attachment.file_type
    )

# مسارات البريد الشخصي
@app.route('/personal-mail')
@login_required
def personal_mail():
    """عرض قائمة البريد الشخصي"""
    # الحصول على البريد الشخصي للمستخدم الحالي
    mails = PersonalMail.query.filter_by(
        user_id=current_user.id,
        is_archived=False
    ).order_by(PersonalMail.date.desc()).all()

    return render_template('personal_mail.html', mails=mails)

@app.route('/personal-mail/create', methods=['GET', 'POST'])
@login_required
def create_personal_mail():
    """إنشاء بريد شخصي جديد"""
    if request.method == 'POST':
        # استخراج البيانات من النموذج
        title = request.form.get('title')
        content = request.form.get('content')
        source = request.form.get('source')
        reference_number = request.form.get('reference_number')
        status = request.form.get('status', 'pending')
        priority = request.form.get('priority', 'normal')
        notes = request.form.get('notes')

        # معالجة التاريخ
        due_date_str = request.form.get('due_date')
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('صيغة تاريخ الاستحقاق غير صحيحة', 'danger')
                return redirect(url_for('create_personal_mail'))

        # إنشاء بريد شخصي جديد
        personal_mail = PersonalMail(
            user_id=current_user.id,
            title=title,
            content=content,
            source=source,
            reference_number=reference_number,
            due_date=due_date,
            status=status,
            priority=priority,
            notes=notes
        )

        # معالجة الملفات المرفقة
        files = request.files.getlist('attachments')
        has_attachments = False

        for file in files:
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash(f'نوع الملف {file.filename} غير مسموح به', 'danger')
                    continue

                # تأمين اسم الملف
                original_filename = secure_filename(file.filename)

                # إنشاء اسم فريد للملف باستخدام UUID
                file_ext = os.path.splitext(original_filename)[1]
                unique_filename = f"{uuid.uuid4().hex}{file_ext}"

                # تحديد مسار الملف
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

                # حفظ الملف
                file.save(file_path)

                # تحديد نوع الملف
                file_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'

                # إنشاء مرفق للبريد الشخصي
                attachment = PersonalMailAttachment(
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    file_type=file_type
                )

                personal_mail.attachments.append(attachment)
                has_attachments = True

        personal_mail.has_attachments = has_attachments

        # حفظ البريد الشخصي في قاعدة البيانات
        db.session.add(personal_mail)
        db.session.commit()

        flash('تم إنشاء البريد الشخصي بنجاح', 'success')
        return redirect(url_for('personal_mail'))

    return render_template('create_personal_mail.html')

@app.route('/personal-mail/<int:id>')
@login_required
def view_personal_mail(id):
    """عرض تفاصيل البريد الشخصي"""
    # الحصول على البريد الشخصي
    mail = PersonalMail.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    if mail.user_id != current_user.id:
        abort(403)  # غير مصرح بالوصول

    return render_template('view_personal_mail.html', mail=mail, now=datetime.now())

@app.route('/personal-mail/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_personal_mail(id):
    """تعديل البريد الشخصي"""
    # الحصول على البريد الشخصي
    mail = PersonalMail.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    if mail.user_id != current_user.id:
        abort(403)  # غير مصرح بالوصول

    if request.method == 'POST':
        # تحديث البيانات
        mail.title = request.form.get('title')
        mail.content = request.form.get('content')
        mail.source = request.form.get('source')
        mail.reference_number = request.form.get('reference_number')
        mail.status = request.form.get('status')
        mail.priority = request.form.get('priority')
        mail.notes = request.form.get('notes')

        # معالجة التاريخ
        due_date_str = request.form.get('due_date')
        if due_date_str:
            try:
                mail.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('صيغة تاريخ الاستحقاق غير صحيحة', 'danger')
                return redirect(url_for('edit_personal_mail', id=id))
        else:
            mail.due_date = None

        # معالجة الملفات المرفقة الجديدة
        files = request.files.getlist('attachments')

        for file in files:
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash(f'نوع الملف {file.filename} غير مسموح به', 'danger')
                    continue

                # تأمين اسم الملف
                original_filename = secure_filename(file.filename)

                # إنشاء اسم فريد للملف باستخدام UUID
                file_ext = os.path.splitext(original_filename)[1]
                unique_filename = f"{uuid.uuid4().hex}{file_ext}"

                # تحديد مسار الملف
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

                # حفظ الملف
                file.save(file_path)

                # تحديد نوع الملف
                file_type = mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'

                # إنشاء مرفق للبريد الشخصي
                attachment = PersonalMailAttachment(
                    personal_mail_id=mail.id,
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    file_type=file_type
                )

                db.session.add(attachment)
                mail.has_attachments = True

        # حفظ التغييرات
        db.session.commit()

        flash('تم تحديث البريد الشخصي بنجاح', 'success')
        return redirect(url_for('view_personal_mail', id=id))

    return render_template('edit_personal_mail.html', mail=mail)

@app.route('/personal-mail/<int:id>/delete', methods=['POST'])
@login_required
def delete_personal_mail(id):
    """حذف البريد الشخصي"""
    # الحصول على البريد الشخصي
    mail = PersonalMail.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    if mail.user_id != current_user.id:
        return jsonify({'error': 'غير مصرح بحذف هذا البريد الشخصي'}), 403

    try:
        # حذف البريد الشخصي (سيتم حذف المرفقات تلقائيًا بسبب cascade)
        db.session.delete(mail)
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم حذف البريد الشخصي بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء حذف البريد الشخصي: {str(e)}'}), 500

@app.route('/personal-mail/<int:id>/archive', methods=['POST'])
@login_required
def archive_personal_mail(id):
    """أرشفة البريد الشخصي"""
    # الحصول على البريد الشخصي
    mail = PersonalMail.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    if mail.user_id != current_user.id:
        return jsonify({'error': 'غير مصرح بأرشفة هذا البريد الشخصي'}), 403

    try:
        # أرشفة البريد الشخصي
        mail.is_archived = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'تم أرشفة البريد الشخصي بنجاح'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء أرشفة البريد الشخصي: {str(e)}'}), 500

@app.route('/personal-mail/<int:id>/change-status', methods=['POST'])
@login_required
def change_personal_mail_status(id):
    """تغيير حالة البريد الشخصي"""
    # الحصول على البريد الشخصي
    mail = PersonalMail.query.get_or_404(id)

    # التحقق من صلاحية الوصول
    if mail.user_id != current_user.id:
        return jsonify({'error': 'غير مصرح بتغيير حالة هذا البريد الشخصي'}), 403

    # الحصول على البيانات
    data = request.get_json()
    new_status = data.get('status')

    if not new_status:
        return jsonify({'error': 'الحالة الجديدة مطلوبة'}), 400

    try:
        # تغيير حالة البريد الشخصي
        mail.status = new_status
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'تم تغيير حالة البريد الشخصي بنجاح',
            'status': mail.get_status_display(),
            'status_color': mail.get_status_color()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'حدث خطأ أثناء تغيير حالة البريد الشخصي: {str(e)}'}), 500

@app.route('/personal-mail/attachments/<int:id>/download')
@login_required
def download_personal_mail_attachment(id):
    """تنزيل مرفق البريد الشخصي"""
    # الحصول على المرفق
    attachment = PersonalMailAttachment.query.get_or_404(id)
    mail = PersonalMail.query.get(attachment.personal_mail_id)

    # التحقق من صلاحية الوصول
    if mail.user_id != current_user.id:
        abort(403)  # غير مصرح بالوصول

    # استخراج اسم الملف من المسار الكامل
    directory = os.path.dirname(attachment.file_path)
    filename = os.path.basename(attachment.file_path)

    # إرسال الملف للتنزيل
    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name=attachment.original_filename
    )

@app.route('/personal-mail/attachments/<int:id>/view')
@login_required
def view_personal_mail_attachment(id):
    """عرض مرفق البريد الشخصي مباشرة في المتصفح"""
    # الحصول على المرفق
    attachment = PersonalMailAttachment.query.get_or_404(id)
    mail = PersonalMail.query.get(attachment.personal_mail_id)

    # التحقق من صلاحية الوصول
    if mail.user_id != current_user.id:
        abort(403)  # غير مصرح بالوصول

    # التحقق من إمكانية عرض الملف في المتصفح
    if not attachment.is_viewable_in_browser():
        return redirect(url_for('download_personal_mail_attachment', id=id))

    # استخراج اسم الملف من المسار الكامل
    directory = os.path.dirname(attachment.file_path)
    filename = os.path.basename(attachment.file_path)

    # إرسال الملف للعرض
    return send_from_directory(
        directory,
        filename,
        as_attachment=False,
        mimetype=attachment.file_type
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
