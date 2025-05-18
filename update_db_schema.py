from app import app, db, Permission

def update_permission_display_names():
    """تحديث أسماء العرض للصلاحيات في قاعدة البيانات"""
    
    with app.app_context():
        # قاموس أسماء الصلاحيات بالعربية
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
        
        # الحصول على جميع الصلاحيات
        permissions = Permission.query.all()
        print(f"تم العثور على {len(permissions)} صلاحية")
        
        # تحديث أسماء العرض
        for permission in permissions:
            if permission.name in permission_names:
                permission.display_name = permission_names[permission.name]
                print(f"تحديث صلاحية {permission.name} إلى {permission.display_name}")
        
        # حفظ التغييرات
        db.session.commit()
        print("تم تحديث أسماء العرض للصلاحيات بنجاح")

if __name__ == "__main__":
    print("بدء تحديث أسماء العرض للصلاحيات...")
    update_permission_display_names()
    print("تم الانتهاء من التحديث")
