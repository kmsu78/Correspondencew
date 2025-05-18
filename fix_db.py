import os
import sqlite3
import glob

def find_database():
    """البحث عن ملف قاعدة البيانات"""
    print("البحث عن ملف قاعدة البيانات...")
    
    # البحث في المجلد الحالي
    db_files = glob.glob('*.db')
    if db_files:
        print(f"تم العثور على قاعدة بيانات في المجلد الحالي: {db_files[0]}")
        return db_files[0]
    
    # البحث في مجلد instance
    if os.path.exists('instance'):
        instance_db_files = [f for f in os.listdir('instance') if f.endswith('.db')]
        if instance_db_files:
            db_path = os.path.join('instance', instance_db_files[0])
            print(f"تم العثور على قاعدة بيانات في مجلد instance: {db_path}")
            return db_path
    
    print("لم يتم العثور على قاعدة بيانات!")
    return None

def fix_database():
    """إصلاح جدول message_status_change في قاعدة البيانات"""
    # البحث عن قاعدة البيانات
    db_path = find_database()
    if not db_path:
        return
    
    # الاتصال بقاعدة البيانات
    print(f"الاتصال بقاعدة البيانات: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # عرض جميع الجداول في قاعدة البيانات
        print("الجداول الموجودة في قاعدة البيانات:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"- {table[0]}")
        
        # التحقق من وجود جدول message_status_change
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_status_change'")
        if not cursor.fetchone():
            print("جدول message_status_change غير موجود في قاعدة البيانات!")
            return
        
        # عرض هيكل جدول message_status_change
        print("\nهيكل جدول message_status_change:")
        cursor.execute("PRAGMA table_info(message_status_change)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
        
        # التحقق من وجود عمود recipient_id
        column_names = [col[1] for col in columns]
        if 'recipient_id' not in column_names:
            print("\nإضافة عمود recipient_id إلى جدول message_status_change...")
            cursor.execute("ALTER TABLE message_status_change ADD COLUMN recipient_id INTEGER")
            conn.commit()
            print("تم إضافة العمود بنجاح!")
        else:
            print("\nالعمود recipient_id موجود بالفعل في الجدول")
        
        # التحقق من الهيكل بعد التعديل
        print("\nهيكل الجدول بعد التعديل:")
        cursor.execute("PRAGMA table_info(message_status_change)")
        updated_columns = cursor.fetchall()
        for col in updated_columns:
            print(f"- {col[1]} ({col[2]})")
        
        print("\nتم إصلاح قاعدة البيانات بنجاح!")
    
    except Exception as e:
        print(f"حدث خطأ: {str(e)}")
    
    finally:
        # إغلاق الاتصال
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_database()
