from flask import Flask
import os
import sqlite3

# إنشاء تطبيق Flask مؤقت للوصول إلى إعدادات قاعدة البيانات
app = Flask(__name__, instance_relative_config=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'correspondence.db')

def update_database():
    """تحديث قاعدة البيانات لإضافة جدول سجل دخول المستخدمين"""
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
        
        # 1. إنشاء جدول سجل دخول المستخدمين إذا لم يكن موجودًا
        print("التحقق من وجود جدول user_login_log...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_login_log'")
        if not cursor.fetchone():
            print("إنشاء جدول user_login_log...")
            cursor.execute("""
                CREATE TABLE user_login_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    login_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(50),
                    user_agent VARCHAR(255),
                    status VARCHAR(20) DEFAULT 'success',
                    FOREIGN KEY (user_id) REFERENCES user(id)
                )
            """)
            print("تم إنشاء جدول user_login_log بنجاح!")
        else:
            print("جدول user_login_log موجود بالفعل")
        
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
