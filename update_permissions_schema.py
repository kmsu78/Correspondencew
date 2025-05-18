from app import app
import sqlite3
import os

def update_database_schema():
    """تحديث مخطط قاعدة البيانات لإضافة الحقول الجديدة للصلاحيات"""

    # الحصول على مسار قاعدة البيانات
    db_path = os.path.join(app.instance_path, 'correspondence.db')

    # التحقق من وجود قاعدة البيانات
    if not os.path.exists(db_path):
        print(f"خطأ: قاعدة البيانات غير موجودة في المسار {db_path}")
        return False

    print(f"جاري تحديث قاعدة البيانات في {db_path}")

    # الاتصال بقاعدة البيانات
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # إنشاء جدول مجموعات الصلاحيات إذا لم يكن موجودًا
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS permission_group (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            display_name VARCHAR(100),
            description VARCHAR(255),
            icon VARCHAR(50),
            "order" INTEGER DEFAULT 0
        )
        """)
        print("تم إنشاء جدول permission_group بنجاح!")

        # التحقق من وجود عمود group_id في جدول permission
        cursor.execute("PRAGMA table_info(permission)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        # إضافة عمود group_id إذا لم يكن موجودًا
        if 'group_id' not in column_names:
            print("إضافة عمود group_id إلى جدول permission...")
            cursor.execute("ALTER TABLE permission ADD COLUMN group_id INTEGER REFERENCES permission_group(id)")
            print("تم إضافة العمود بنجاح!")
        else:
            print("العمود group_id موجود بالفعل في جدول permission")

        # إضافة عمود is_critical إذا لم يكن موجودًا
        if 'is_critical' not in column_names:
            print("إضافة عمود is_critical إلى جدول permission...")
            cursor.execute("ALTER TABLE permission ADD COLUMN is_critical BOOLEAN DEFAULT 0")
            print("تم إضافة العمود بنجاح!")
        else:
            print("العمود is_critical موجود بالفعل في جدول permission")

        # تحديث نموذج سجل تغييرات الصلاحيات
        cursor.execute("PRAGMA table_info(permission_change)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]

        # تحديث أنواع البيانات لحقول old_value و new_value
        print("تحديث أنواع البيانات لحقول old_value و new_value...")
        try:
            # إنشاء جدول مؤقت بالهيكل الصحيح
            cursor.execute("""
            CREATE TABLE permission_change_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                changed_by_id INTEGER NOT NULL,
                permission_type VARCHAR(50) NOT NULL,
                old_value VARCHAR(255) NOT NULL,
                new_value VARCHAR(255) NOT NULL,
                change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                permission_id INTEGER REFERENCES permission(id),
                role_id INTEGER REFERENCES role(id),
                FOREIGN KEY (user_id) REFERENCES user (id),
                FOREIGN KEY (changed_by_id) REFERENCES user (id)
            )
            """)

            # نقل البيانات من الجدول القديم إلى الجدول المؤقت
            cursor.execute("""
            INSERT INTO permission_change_temp (id, user_id, changed_by_id, permission_type, old_value, new_value, change_date, notes, permission_id, role_id)
            SELECT id, user_id, changed_by_id, permission_type, old_value, new_value, change_date, notes, permission_id, role_id FROM permission_change
            """)

            # حذف الجدول القديم
            cursor.execute("DROP TABLE permission_change")

            # إعادة تسمية الجدول المؤقت
            cursor.execute("ALTER TABLE permission_change_temp RENAME TO permission_change")

            print("تم تحديث أنواع البيانات بنجاح!")
        except Exception as e:
            print(f"حدث خطأ أثناء تحديث أنواع البيانات: {str(e)}")

        # إضافة عمود permission_id إذا لم يكن موجودًا
        if 'permission_id' not in column_names:
            print("إضافة عمود permission_id إلى جدول permission_change...")
            cursor.execute("ALTER TABLE permission_change ADD COLUMN permission_id INTEGER REFERENCES permission(id)")
            print("تم إضافة العمود بنجاح!")
        else:
            print("العمود permission_id موجود بالفعل في جدول permission_change")

        # إضافة عمود role_id إذا لم يكن موجودًا
        if 'role_id' not in column_names:
            print("إضافة عمود role_id إلى جدول permission_change...")
            cursor.execute("ALTER TABLE permission_change ADD COLUMN role_id INTEGER REFERENCES role(id)")
            print("تم إضافة العمود بنجاح!")
        else:
            print("العمود role_id موجود بالفعل في جدول permission_change")

        # حفظ التغييرات
        conn.commit()
        print("تم تحديث مخطط قاعدة البيانات بنجاح!")
        return True

    except Exception as e:
        # التراجع عن التغييرات في حالة حدوث خطأ
        conn.rollback()
        print(f"حدث خطأ أثناء تحديث مخطط قاعدة البيانات: {str(e)}")
        return False

    finally:
        # إغلاق الاتصال بقاعدة البيانات
        conn.close()

if __name__ == "__main__":
    # إنشاء مجلد instance إذا لم يكن موجودًا
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    # تحديث مخطط قاعدة البيانات
    success = update_database_schema()

    if success:
        print("تم تنفيذ العملية بنجاح!")
    else:
        print("فشلت العملية!")
