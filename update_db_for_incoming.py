import os
import sqlite3
import sys
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
    
    # التحقق من وجود الملفات
    for path in possible_paths:
        if os.path.exists(path):
            print(f"تم العثور على قاعدة البيانات في: {path}")
            return path
    
    print("لم يتم العثور على قاعدة البيانات!")
    return None

def update_database_schema():
    """تحديث هيكل قاعدة البيانات لدعم الرسائل الواردة"""
    print("جاري تحديث هيكل قاعدة البيانات...")
    
    # البحث عن ملف قاعدة البيانات
    db_path = find_database_file()
    if not db_path:
        print("لم يتم العثور على قاعدة البيانات")
        return False
    
    try:
        # الاتصال بقاعدة البيانات
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # التحقق من وجود عمود sender_entity في جدول message
        cursor.execute("PRAGMA table_info(message)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'sender_entity' not in columns:
            print("إضافة عمود sender_entity إلى جدول message...")
            cursor.execute("ALTER TABLE message ADD COLUMN sender_entity VARCHAR(200)")
            conn.commit()
            print("تم إضافة العمود بنجاح")
        else:
            print("العمود sender_entity موجود بالفعل")
        
        # إغلاق الاتصال
        conn.close()
        print("تم تحديث هيكل قاعدة البيانات بنجاح")
        return True
    
    except Exception as e:
        print(f"حدث خطأ أثناء تحديث قاعدة البيانات: {str(e)}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    print("بدء تحديث قاعدة البيانات لدعم الرسائل الواردة...")
    success = update_database_schema()
    
    if success:
        print("تم تحديث قاعدة البيانات بنجاح")
    else:
        print("فشل تحديث قاعدة البيانات")
        sys.exit(1)
