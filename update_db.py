from flask import Flask
import os
import sqlite3

# إنشاء تطبيق Flask مؤقت للوصول إلى إعدادات قاعدة البيانات
app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'correspondence.db')

def update_database():
    """تحديث قاعدة البيانات لإضافة الأعمدة الجديدة"""
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

        # 1. التحقق من وجود العمود has_attachments في جدول message
        cursor.execute("PRAGMA table_info(message)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        if 'has_attachments' not in column_names:
            print("إضافة العمود has_attachments إلى جدول message...")

            # إضافة العمود الجديد
            cursor.execute("ALTER TABLE message ADD COLUMN has_attachments BOOLEAN DEFAULT 0")

            # تحديث قيم العمود الجديد بناءً على وجود مرفقات
            cursor.execute("""
                UPDATE message
                SET has_attachments = (
                    SELECT CASE WHEN COUNT(*) > 0 THEN 1 ELSE 0 END
                    FROM attachment
                    WHERE attachment.message_id = message.id
                )
            """)

            print("تم تحديث جدول message بنجاح!")
        else:
            print("العمود has_attachments موجود بالفعل في جدول message")

        # 2. التحقق من وجود الأعمدة الجديدة في جدول user
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        # إضافة عمود can_change_status إذا لم يكن موجودًا
        if 'can_change_status' not in column_names:
            print("إضافة عمود can_change_status إلى جدول user...")
            cursor.execute("ALTER TABLE user ADD COLUMN can_change_status BOOLEAN DEFAULT 0")
        else:
            print("العمود can_change_status موجود بالفعل في جدول user")

        # إضافة عمود can_manage_status_permissions إذا لم يكن موجودًا
        if 'can_manage_status_permissions' not in column_names:
            print("إضافة عمود can_manage_status_permissions إلى جدول user...")
            cursor.execute("ALTER TABLE user ADD COLUMN can_manage_status_permissions BOOLEAN DEFAULT 0")
        else:
            print("العمود can_manage_status_permissions موجود بالفعل في جدول user")

        # تحديث صلاحيات المشرفين
        print("تحديث صلاحيات المشرفين...")
        cursor.execute("UPDATE user SET can_change_status = 1, can_manage_status_permissions = 1 WHERE role = 'admin'")

        # 3. إنشاء جدول سجل تغييرات الصلاحيات إذا لم يكن موجودًا
        print("التحقق من وجود جدول permission_change...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='permission_change'")
        if not cursor.fetchone():
            print("إنشاء جدول permission_change...")
            cursor.execute("""
                CREATE TABLE permission_change (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    changed_by_id INTEGER NOT NULL,
                    permission_type VARCHAR(50) NOT NULL,
                    old_value BOOLEAN NOT NULL,
                    new_value BOOLEAN NOT NULL,
                    change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES user (id),
                    FOREIGN KEY (changed_by_id) REFERENCES user (id)
                )
            """)
            print("تم إنشاء جدول permission_change بنجاح!")
        else:
            print("جدول permission_change موجود بالفعل")

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
