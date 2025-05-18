from flask import Flask
import os
import sqlite3

# إنشاء تطبيق Flask مؤقت للوصول إلى إعدادات قاعدة البيانات
app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'correspondence.db')

def update_database():
    """تحديث قاعدة البيانات لإضافة جداول الأدوار والصلاحيات"""
    try:
        # الحصول على مسار قاعدة البيانات
        db_path = os.path.join(app.instance_path, 'correspondence.db')

        # التحقق من وجود قاعدة البيانات
        if not os.path.exists(db_path):
            print(f"قاعدة البيانات غير موجودة في المسار: {db_path}")
            return False

        # إنشاء اتصال بقاعدة البيانات
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. إنشاء جدول الصلاحيات إذا لم يكن موجودًا
        print("التحقق من وجود جدول permission...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='permission'")
        if not cursor.fetchone():
            print("إنشاء جدول permission...")
            cursor.execute("""
                CREATE TABLE permission (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    description VARCHAR(255)
                )
            """)
            print("تم إنشاء جدول permission بنجاح!")

            # إضافة الصلاحيات الأساسية
            print("إضافة الصلاحيات الأساسية...")
            default_permissions = [
                ('manage_users', 'إدارة المستخدمين', 'إدارة المستخدمين'),
                ('manage_departments', 'إدارة الأقسام', 'إدارة الأقسام'),
                ('manage_roles', 'إدارة الأدوار والصلاحيات', 'إدارة الأدوار والصلاحيات'),
                ('manage_permissions', 'إدارة صلاحيات المستخدمين', 'إدارة صلاحيات المستخدمين'),
                ('change_message_status', 'تغيير حالة الرسائل', 'تغيير حالة الرسائل'),
                ('view_reports', 'عرض التقارير', 'عرض التقارير'),
                ('view_all_messages', 'عرض جميع الرسائل', 'عرض جميع الرسائل'),
                ('delete_messages', 'حذف الرسائل', 'حذف الرسائل')
            ]

            cursor.executemany(
                "INSERT INTO permission (name, description, display_name) VALUES (?, ?, ?)",
                default_permissions
            )
            print("تم إضافة الصلاحيات الأساسية بنجاح!")
        else:
            print("جدول permission موجود بالفعل")

        # 2. إنشاء جدول الأدوار إذا لم يكن موجودًا
        print("التحقق من وجود جدول role...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='role'")
        if not cursor.fetchone():
            print("إنشاء جدول role...")
            cursor.execute("""
                CREATE TABLE role (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(50) NOT NULL UNIQUE,
                    description VARCHAR(255),
                    is_system BOOLEAN DEFAULT 0
                )
            """)
            print("تم إنشاء جدول role بنجاح!")

            # إضافة الأدوار الأساسية
            print("إضافة الأدوار الأساسية...")
            default_roles = [
                ('admin', 'مدير النظام', 1),
                ('user', 'مستخدم عادي', 1),
                ('manager', 'مدير', 0),
                ('supervisor', 'مشرف', 0)
            ]

            cursor.executemany(
                "INSERT INTO role (name, description, is_system) VALUES (?, ?, ?)",
                default_roles
            )
            print("تم إضافة الأدوار الأساسية بنجاح!")
        else:
            print("جدول role موجود بالفعل")

        # 3. إنشاء جدول العلاقة بين الأدوار والصلاحيات
        print("التحقق من وجود جدول role_permissions...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='role_permissions'")
        if not cursor.fetchone():
            print("إنشاء جدول role_permissions...")
            cursor.execute("""
                CREATE TABLE role_permissions (
                    role_id INTEGER NOT NULL,
                    permission_id INTEGER NOT NULL,
                    PRIMARY KEY (role_id, permission_id),
                    FOREIGN KEY (role_id) REFERENCES role(id),
                    FOREIGN KEY (permission_id) REFERENCES permission(id)
                )
            """)
            print("تم إنشاء جدول role_permissions بنجاح!")

            # إضافة صلاحيات للأدوار
            print("إضافة صلاحيات للأدوار...")

            # الحصول على معرف دور المدير
            cursor.execute("SELECT id FROM role WHERE name = 'manager'")
            manager_role_id = cursor.fetchone()[0]

            # الحصول على معرفات الصلاحيات
            cursor.execute("SELECT id FROM permission WHERE name = 'change_message_status'")
            change_status_id = cursor.fetchone()[0]

            cursor.execute("SELECT id FROM permission WHERE name = 'view_reports'")
            view_reports_id = cursor.fetchone()[0]

            # إضافة صلاحيات لدور المدير
            role_permissions = [
                (manager_role_id, change_status_id),
                (manager_role_id, view_reports_id)
            ]

            cursor.executemany(
                "INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)",
                role_permissions
            )
            print("تم إضافة صلاحيات للأدوار بنجاح!")
        else:
            print("جدول role_permissions موجود بالفعل")

        # 4. تحديث جدول المستخدمين لإضافة حقل role_id
        print("التحقق من وجود حقل role_id في جدول user...")
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        if 'role_id' not in column_names:
            print("إضافة حقل role_id إلى جدول user...")
            cursor.execute("ALTER TABLE user ADD COLUMN role_id INTEGER REFERENCES role(id)")
            print("تم إضافة حقل role_id بنجاح!")

            # تحديث role_id بناءً على role الحالي
            print("تحديث role_id للمستخدمين الحاليين...")

            # الحصول على معرفات الأدوار
            cursor.execute("SELECT id FROM role WHERE name = 'admin'")
            admin_role_id = cursor.fetchone()[0]

            cursor.execute("SELECT id FROM role WHERE name = 'user'")
            user_role_id = cursor.fetchone()[0]

            # تحديث المستخدمين
            cursor.execute("UPDATE user SET role_id = ? WHERE role = 'admin'", (admin_role_id,))
            cursor.execute("UPDATE user SET role_id = ? WHERE (role IS NULL OR role = 'user' OR role = '')", (user_role_id,))

            print("تم تحديث role_id للمستخدمين الحاليين بنجاح!")
        else:
            print("حقل role_id موجود بالفعل في جدول user")

        # حفظ التغييرات
        conn.commit()
        print("تم تحديث قاعدة البيانات بنجاح!")

        # إغلاق الاتصال
        conn.close()
        return True

    except Exception as e:
        print(f"حدث خطأ أثناء تحديث قاعدة البيانات: {str(e)}")
        return False

# تشغيل وظيفة تحديث قاعدة البيانات
if __name__ == "__main__":
    # التأكد من وجود مجلد instance
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # تحديث قاعدة البيانات
    if update_database():
        print("تم تحديث قاعدة البيانات بنجاح!")
    else:
        print("فشل تحديث قاعدة البيانات.")
