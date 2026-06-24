import os
import sys
import platform
import subprocess

def ensure_psutil():
    try:
        import psutil
        return psutil
    except ImportError:
        print("⚠️ مكتبة 'psutil' غير موجودة. جاري التثبيت التلقائي...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
            import psutil
            print("✅ تم تثبيت psutil بنجاح!")
            return psutil
        except Exception as e:
            print(f"❌ فشل التثبيت التلقائي: {e}")
            sys.exit(1)

def run_monitor():
    psutil = ensure_psutil()
    print("=" * 40)
    print("        📊 نظام المراقبة الذكي")
    print("=" * 40)
    
    print(f"🖥️  نظام التشغيل: {platform.system()} {platform.release()}")
    print(f"🐍 نسخة البايثون: {platform.python_version()}")
    
    print("\n[المعالج - CPU]")
    print(f"⚡ نسبة الاستهلاك: {psutil.cpu_percent(interval=1)}%")
    print(f"🧠 عدد الأنوية (المنطقية): {psutil.cpu_count(logical=True)}")
    
    print("\n[الذاكرة - RAM]")
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024 ** 3)
    used_gb = mem.used / (1024 ** 3)
    print(f"💾 الذاكرة الإجمالية: {total_gb:.2f} GB")
    print(f"🔴 الذاكرة المستهلكة: {used_gb:.2f} GB ({mem.percent}%)")
    
    print("\n[القرص الصلب - Disk]")
    disk = psutil.disk_usage('/')
    total_disk = disk.total / (1024 ** 3)
    used_disk = disk.used / (1024 ** 3)
    print(f"💽 المساحة الإجمالية: {total_disk:.2f} GB")
    print(f"📂 المساحة المستهلكة: {used_disk:.2f} GB ({disk.percent}%)")
    
    print("=" * 40)

if __name__ == "__main__":
    run_monitor()
