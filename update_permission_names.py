import sqlite3
import os
import sys

# تحديد مسار قاعدة البيانات
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'correspondence.db')

# تكوين الطباعة للتأكد من ظهور المخرجات
def print_flush(message):
    print(message)
    sys.stdout.flush()

def update_permission_names():
    """تحديث أسماء الصلاحيات في قاعدة البيانات لتكون بالعربية"""

    # الحصول على مسار قاعدة البيانات
    db_path = DB_PATH
    print_flush(f"مسار قاعدة البيانات: {db_path}")

    # التحقق من وجود قاعدة البيانات
    if not os.path.exists(db_path):
        print_flush(f"خطأ: قاعدة البيانات غير موجودة في المسار {db_path}")
        return False

    print_flush("تم العثور على قاعدة البيانات بنجاح")

    # الاتصال بقاعدة البيانات
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # التحقق من وجود عمود display_name في جدول permission
        cursor.execute("PRAGMA table_info(permission)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        print_flush(f"أعمدة جدول permission: {column_names}")

        # إضافة عمود display_name إذا لم يكن موجودًا
        if 'display_name' not in column_names:
            print_flush("إضافة عمود display_name إلى جدول permission...")
            cursor.execute("ALTER TABLE permission ADD COLUMN display_name VARCHAR(100)")
            print_flush("تم إضافة العمود بنجاح!")
        else:
            print_flush("العمود display_name موجود بالفعل في جدول permission")

        # تحديث أسماء العرض للصلاحيات
        permission_names = {
            'manage_users': 'إدارة المستخدمين',
            'manage_departments': 'إدارة الأقسام',
            'manage_roles': 'إدارة الأدوار والصلاحيات',
            'manage_permissions': 'إدارة صلاحيات المستخدمين',
            'change_message_status': 'تغيير حالة الرسائل',
            'view_reports': 'عرض التقارير',
            'view_all_messages': 'عرض جميع الرسائل',
            'delete_messages': 'حذف الرسائل'
        }

        # الحصول على قائمة الصلاحيات الحالية
        cursor.execute("SELECT id, name FROM permission")
        permissions = cursor.fetchall()
        print_flush(f"الصلاحيات الموجودة: {permissions}")

        # تحديث أسماء العرض
        for permission_id, permission_name in permissions:
            display_name = permission_names.get(permission_name, permission_name)
            cursor.execute(
                "UPDATE permission SET display_name = ? WHERE id = ?",
                (display_name, permission_id)
            )
            print_flush(f"تم تحديث اسم العرض للصلاحية {permission_name} إلى {display_name}")

        # حفظ التغييرات
        conn.commit()
        print_flush("تم تحديث أسماء الصلاحيات بنجاح!")
        return True

    except Exception as e:
        # التراجع عن التغييرات في حالة حدوث خطأ
        conn.rollback()
        print_flush(f"حدث خطأ أثناء تحديث أسماء الصلاحيات: {str(e)}")
        import traceback
        print_flush(traceback.format_exc())
        return False

    finally:
        # إغلاق الاتصال بقاعدة البيانات
        conn.close()

if __name__ == "__main__":
    print_flush("بدء تنفيذ البرنامج...")

    # إنشاء مجلد instance إذا لم يكن موجودًا
    instance_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(instance_dir):
        print_flush(f"إنشاء مجلد instance في {instance_dir}")
        os.makedirs(instance_dir)
    else:
        print_flush(f"مجلد instance موجود بالفعل في {instance_dir}")

    # تحديث أسماء الصلاحيات
    print_flush("بدء تحديث أسماء الصلاحيات...")
    success = update_permission_names()

    if success:
        print_flush("تم تنفيذ العملية بنجاح!")
    else:
        print_flush("فشلت العملية!")
