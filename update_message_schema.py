import os
import sqlite3
from app import app, db, Message
from datetime import datetime
import glob

def find_database_file():
    """البحث عن ملف قاعدة البيانات في المجلدات المحتملة"""
    # المسارات المحتملة لقاعدة البيانات
    possible_paths = [
        os.path.join(app.instance_path, 'app.db'),
        os.path.join(os.getcwd(), 'app.db'),
        os.path.join(os.getcwd(), 'instance', 'app.db')
    ]

    # البحث عن أي ملف .db في المجلد الحالي
    db_files = glob.glob('*.db')
    if db_files:
        possible_paths.append(os.path.join(os.getcwd(), db_files[0]))

    # البحث عن أي ملف .db في مجلد instance
    instance_db_files = glob.glob(os.path.join('instance', '*.db'))
    if instance_db_files:
        possible_paths.append(os.path.join(os.getcwd(), instance_db_files[0]))

    # التحقق من وجود الملفات
    for path in possible_paths:
        if os.path.exists(path):
            print(f"تم العثور على قاعدة البيانات في: {path}")
            return path

    return None

def update_message_schema():
    """تحديث هيكل جدول الرسائل لإضافة الحقول الجديدة"""

    # البحث عن ملف قاعدة البيانات
    db_path = find_database_file()

    # التحقق من وجود قاعدة البيانات
    if not db_path:
        print("لم يتم العثور على قاعدة البيانات. يرجى التأكد من وجود ملف قاعدة البيانات.")
        return

    print(f"جاري تحديث هيكل جدول الرسائل في قاعدة البيانات: {db_path}")

    # الاتصال بقاعدة البيانات
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # التحقق من وجود جدول الرسائل
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message'")
        if not cursor.fetchone():
            print("خطأ: جدول 'message' غير موجود في قاعدة البيانات!")
            print("جاري عرض الجداول الموجودة في قاعدة البيانات:")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table in tables:
                print(f"- {table[0]}")
            return

        # التحقق من وجود الأعمدة الجديدة
        cursor.execute("PRAGMA table_info(message)")
        columns_info = cursor.fetchall()
        columns = [column[1] for column in columns_info]

        print("الأعمدة الموجودة حالياً في جدول message:")
        for col in columns_info:
            print(f"- {col[1]} ({col[2]})")

        # إضافة الأعمدة الجديدة إذا لم تكن موجودة
        columns_to_add = []

        if 'priority' not in columns:
            columns_to_add.append(("priority", "VARCHAR(20) DEFAULT 'normal'"))

        if 'message_type' not in columns:
            columns_to_add.append(("message_type", "VARCHAR(30)"))

        if 'confidentiality' not in columns:
            columns_to_add.append(("confidentiality", "VARCHAR(20) DEFAULT 'normal'"))

        if 'reference_number' not in columns:
            columns_to_add.append(("reference_number", "VARCHAR(50)"))

        if 'due_date' not in columns:
            columns_to_add.append(("due_date", "DATE"))

        # إضافة الأعمدة الجديدة
        for column_name, column_type in columns_to_add:
            try:
                print(f"إضافة عمود {column_name}...")
                cursor.execute(f"ALTER TABLE message ADD COLUMN {column_name} {column_type}")
                conn.commit()
                print(f"تم إضافة عمود {column_name} بنجاح!")
            except Exception as column_error:
                print(f"خطأ أثناء إضافة عمود {column_name}: {str(column_error)}")
                # نستمر مع العمود التالي حتى لو فشل هذا العمود

        # التحقق من الأعمدة بعد التحديث
        cursor.execute("PRAGMA table_info(message)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print("\nالأعمدة بعد التحديث:")
        for col in updated_columns:
            print(f"- {col}")

        # حفظ التغييرات النهائية
        conn.commit()
        print("\nتم تحديث هيكل جدول الرسائل بنجاح!")

    except Exception as e:
        conn.rollback()
        print(f"حدث خطأ أثناء تحديث هيكل جدول الرسائل: {str(e)}")
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
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    # تحديث هيكل جدول الرسائل
    update_message_schema()
