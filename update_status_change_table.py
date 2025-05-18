import os
import sqlite3
import glob

def find_database_file():
    """البحث عن ملف قاعدة البيانات في المجلدات المحتملة"""
    print("البحث عن ملف قاعدة البيانات...")

    # المسارات المحتملة لقاعدة البيانات
    possible_paths = [
        'instance/app.db',
        'app.db',
        'instance/correspondence.db',
        'correspondence.db'
    ]

    # البحث عن أي ملف .db في المجلد الحالي
    db_files = glob.glob('*.db')
    for db_file in db_files:
        possible_paths.append(db_file)

    # البحث عن أي ملف .db في مجلد instance
    if os.path.exists('instance'):
        instance_db_files = [os.path.join('instance', f) for f in os.listdir('instance') if f.endswith('.db')]
        for db_file in instance_db_files:
            possible_paths.append(db_file)

    print(f"المسارات المحتملة: {possible_paths}")

    # التحقق من وجود الملفات
    for path in possible_paths:
        if os.path.exists(path):
            print(f"تم العثور على قاعدة البيانات في: {path}")
            return path

    return None

def update_message_status_change_table():
    """تحديث هيكل جدول message_status_change لإضافة عمود recipient_id"""

    # البحث عن ملف قاعدة البيانات
    db_path = find_database_file()

    # التحقق من وجود قاعدة البيانات
    if not db_path:
        print("لم يتم العثور على قاعدة البيانات. يرجى التأكد من وجود ملف قاعدة البيانات.")
        return

    print(f"جاري تحديث هيكل جدول message_status_change في قاعدة البيانات: {db_path}")

    # الاتصال بقاعدة البيانات
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # التحقق من وجود جدول message_status_change
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_status_change'")
        if not cursor.fetchone():
            print("خطأ: جدول 'message_status_change' غير موجود في قاعدة البيانات!")
            print("جاري عرض الجداول الموجودة في قاعدة البيانات:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table in tables:
                print(f"- {table[0]}")
            return

        # التحقق من وجود عمود recipient_id
        cursor.execute("PRAGMA table_info(message_status_change)")
        columns_info = cursor.fetchall()
        columns = [column[1] for column in columns_info]

        print("الأعمدة الموجودة حالياً في جدول message_status_change:")
        for col in columns_info:
            print(f"- {col[1]} ({col[2]})")

        # إضافة عمود recipient_id إذا لم يكن موجوداً
        if 'recipient_id' not in columns:
            print("إضافة عمود recipient_id...")
            cursor.execute("ALTER TABLE message_status_change ADD COLUMN recipient_id INTEGER REFERENCES user(id)")
            conn.commit()
            print("تم إضافة عمود recipient_id بنجاح!")
        else:
            print("العمود recipient_id موجود بالفعل في جدول message_status_change")

        # التحقق من الأعمدة بعد التحديث
        cursor.execute("PRAGMA table_info(message_status_change)")
        updated_columns = cursor.fetchall()
        print("\nالأعمدة بعد التحديث:")
        for col in updated_columns:
            print(f"- {col[1]} ({col[2]})")

        # حفظ التغييرات النهائية
        conn.commit()
        print("\nتم تحديث هيكل جدول message_status_change بنجاح!")

    except Exception as e:
        conn.rollback()
        print(f"حدث خطأ أثناء تحديث هيكل جدول message_status_change: {str(e)}")
        print("معلومات إضافية للتشخيص:")
        try:
            # محاولة الحصول على معلومات حول قاعدة البيانات
            cursor.execute("PRAGMA database_list")
            db_info = cursor.fetchall()
            print("قواعد البيانات المتصلة:")
            for db in db_info:
                print(f"- {db}")
        except Exception as db_error:
            print(f"خطأ أثناء الحصول على معلومات قاعدة البيانات: {str(db_error)}")

    finally:
        # إغلاق الاتصال
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # إنشاء مجلد instance إذا لم يكن موجودًا
    if not os.path.exists('instance'):
        os.makedirs('instance')

    # تحديث هيكل جدول message_status_change
    update_message_status_change_table()
