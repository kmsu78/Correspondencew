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
    """تحديث هيكل قاعدة البيانات لدعم البريد الشخصي"""
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
        
        # التحقق من وجود جدول personal_mail
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='personal_mail'")
        if not cursor.fetchone():
            print("إنشاء جدول personal_mail...")
            cursor.execute("""
            CREATE TABLE personal_mail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                content TEXT,
                source VARCHAR(200),
                reference_number VARCHAR(100),
                date DATETIME,
                due_date DATE,
                status VARCHAR(20),
                priority VARCHAR(20),
                notes TEXT,
                has_attachments BOOLEAN,
                is_archived BOOLEAN,
                FOREIGN KEY (user_id) REFERENCES user (id)
            )
            """)
            print("تم إنشاء جدول personal_mail بنجاح")
        else:
            print("جدول personal_mail موجود بالفعل")
        
        # التحقق من وجود جدول personal_mail_attachment
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='personal_mail_attachment'")
        if not cursor.fetchone():
            print("إنشاء جدول personal_mail_attachment...")
            cursor.execute("""
            CREATE TABLE personal_mail_attachment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personal_mail_id INTEGER NOT NULL,
                filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_size INTEGER,
                file_type VARCHAR(100),
                upload_date DATETIME,
                FOREIGN KEY (personal_mail_id) REFERENCES personal_mail (id)
            )
            """)
            print("تم إنشاء جدول personal_mail_attachment بنجاح")
        else:
            print("جدول personal_mail_attachment موجود بالفعل")
        
        # إغلاق الاتصال
        conn.close()
        print("تم تحديث هيكل قاعدة البيانات بنجاح")
        return True
    
    except Exception as e:
        print(f"حدث خطأ أثناء تحديث قاعدة البيانات: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    print("بدء تحديث قاعدة البيانات لدعم البريد الشخصي...")
    success = update_database_schema()
    
    if success:
        print("تم تحديث قاعدة البيانات بنجاح")
    else:
        print("فشل تحديث قاعدة البيانات")
        sys.exit(1)
