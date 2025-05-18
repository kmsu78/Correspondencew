import os
from app import app, db, User, Role, PermissionGroup, Permission
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

def init_db():
    """تهيئة قاعدة البيانات وإنشاء البيانات الأولية"""
    with app.app_context():
        # إنشاء جداول قاعدة البيانات
        db.create_all()

        # التحقق من وجود الأدوار
        if Role.query.count() == 0:
            print("إنشاء الأدوار الافتراضية...")
            roles = [
                Role(name="مدير النظام", description="صلاحيات كاملة للنظام"),
                Role(name="مستخدم عادي", description="صلاحيات محدودة للمستخدمين العاديين"),
                Role(name="مشرف", description="صلاحيات إشرافية على المستخدمين")
            ]
            db.session.add_all(roles)
            db.session.commit()

        # التحقق من وجود مجموعات الصلاحيات
        if PermissionGroup.query.count() == 0:
            print("إنشاء مجموعات الصلاحيات الافتراضية...")
            groups = [
                PermissionGroup(name="user_management", display_name="إدارة المستخدمين", description="صلاحيات إدارة المستخدمين وحساباتهم", icon="fa-users", order=1),
                PermissionGroup(name="message_management", display_name="إدارة الرسائل", description="صلاحيات إدارة الرسائل والمراسلات", icon="fa-envelope", order=2),
                PermissionGroup(name="status_management", display_name="إدارة الحالات", description="صلاحيات إدارة حالات الرسائل", icon="fa-tasks", order=3),
                PermissionGroup(name="system_management", display_name="إدارة النظام", description="صلاحيات إدارة إعدادات النظام", icon="fa-cogs", order=4)
            ]
            db.session.add_all(groups)
            db.session.commit()

        # التحقق من وجود الصلاحيات
        if Permission.query.count() == 0:
            print("إنشاء الصلاحيات الافتراضية...")
            # الحصول على مجموعات الصلاحيات
            user_group = PermissionGroup.query.filter_by(name="user_management").first()
            message_group = PermissionGroup.query.filter_by(name="message_management").first()
            status_group = PermissionGroup.query.filter_by(name="status_management").first()
            system_group = PermissionGroup.query.filter_by(name="system_management").first()

            permissions = [
                # صلاحيات إدارة المستخدمين
                Permission(name="view_users", display_name="عرض المستخدمين", description="عرض قائمة المستخدمين", group_id=user_group.id),
                Permission(name="add_user", display_name="إضافة مستخدم", description="إضافة مستخدمين جدد", group_id=user_group.id),
                Permission(name="edit_user", display_name="تعديل مستخدم", description="تعديل بيانات المستخدمين", group_id=user_group.id),
                Permission(name="delete_user", display_name="حذف مستخدم", description="حذف المستخدمين", group_id=user_group.id),
                Permission(name="manage_permissions", display_name="إدارة الصلاحيات", description="إدارة صلاحيات المستخدمين", group_id=user_group.id),

                # صلاحيات إدارة الرسائل
                Permission(name="view_all_messages", display_name="عرض جميع الرسائل", description="عرض جميع الرسائل في النظام", group_id=message_group.id),
                Permission(name="send_message", display_name="إرسال رسالة", description="إرسال رسائل جديدة", group_id=message_group.id),
                Permission(name="delete_message", display_name="حذف رسالة", description="حذف الرسائل", group_id=message_group.id),

                # صلاحيات إدارة الحالات
                Permission(name="change_status", display_name="تغيير الحالة", description="تغيير حالة الرسائل", group_id=status_group.id),
                Permission(name="view_status_history", display_name="عرض سجل الحالات", description="عرض سجل تغييرات الحالة", group_id=status_group.id),

                # صلاحيات إدارة النظام
                Permission(name="manage_system", display_name="إدارة النظام", description="إدارة إعدادات النظام", group_id=system_group.id),
                Permission(name="view_logs", display_name="عرض السجلات", description="عرض سجلات النظام", group_id=system_group.id)
            ]
            db.session.add_all(permissions)
            db.session.commit()

        # التحقق من وجود مستخدم مدير النظام
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("إنشاء مستخدم مدير النظام الافتراضي...")
            admin_role = Role.query.filter_by(name="مدير النظام").first()

            # إنشاء مستخدم مدير النظام
            admin = User(
                username="admin",
                email=os.environ.get('ADMIN_EMAIL', 'admin@example.com'),
                password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123')),
                full_name="مدير النظام",
                department='IT',
                role='admin',  # للتوافق مع الإصدارات السابقة
                role_id=admin_role.id if admin_role else None,
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()

            print(f"تم إنشاء مستخدم مدير النظام: {admin.username}")
            print(f"البريد الإلكتروني: {admin.email}")
            print(f"كلمة المرور: {os.environ.get('ADMIN_PASSWORD', 'admin123')}")
            print("يرجى تغيير كلمة المرور بعد تسجيل الدخول لأول مرة.")
        else:
            print("مستخدم مدير النظام موجود بالفعل.")

if __name__ == '__main__':
    init_db()
