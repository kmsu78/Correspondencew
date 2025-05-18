from app import app, db
import sqlite3
import os

def update_database_schema():
    """تحديث مخطط قاعدة البيانات لإضافة حقل التوقيع للمستخدمين"""
    
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
        # التحقق من وجود عمود signature في جدول user
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        # إضافة عمود signature إذا لم يكن موجودًا
        if 'signature' not in column_names:
            print("إضافة عمود signature إلى جدول user...")
            cursor.execute("ALTER TABLE user ADD COLUMN signature TEXT")
            print("تم إضافة العمود بنجاح!")
            
            # حفظ التغييرات
            conn.commit()
            print("تم تحديث مخطط قاعدة البيانات بنجاح!")
            return True
        else:
            print("العمود signature موجود بالفعل في جدول user")
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
