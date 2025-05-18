import os
import sys
import time

def run_script(script_name):
    """تشغيل سكريبت بايثون وعرض النتيجة"""
    print(f"\n{'='*50}")
    print(f"تشغيل سكريبت: {script_name}")
    print(f"{'='*50}")
    
    # تشغيل السكريبت
    exit_code = os.system(f"python {script_name}")
    
    if exit_code == 0:
        print(f"\n✅ تم تنفيذ السكريبت {script_name} بنجاح!")
    else:
        print(f"\n❌ فشل تنفيذ السكريبت {script_name} برمز خروج {exit_code}")
        sys.exit(exit_code)
    
    # انتظار قليلاً بين السكريبتات
    time.sleep(1)

def main():
    """تشغيل جميع سكريبتات تحديث الصلاحيات بالترتيب الصحيح"""
    print("بدء تحديث نظام الصلاحيات...")
    
    # تحديث مخطط قاعدة البيانات أولاً
    run_script("update_permissions_schema.py")
    
    # تحديث الصلاحيات
    run_script("update_permissions.py")
    
    # تحديث مجموعات الصلاحيات
    run_script("update_permission_groups.py")
    
    print("\n🎉 تم تحديث نظام الصلاحيات بنجاح!")

if __name__ == "__main__":
    main()
