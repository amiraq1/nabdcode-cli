#!/data/data/com.termux/files/usr/bin/bash

# الانتقال إلى مجلد المشروع لضمان استيراد الوحدات بشكل سليم
cd /data/data/com.termux/files/home/nabdcode-cli

# تشغيل خادم الـ MCP باستخدام مفسر بايثون المباشر وتمرير الوسيطات
exec /data/data/com.termux/files/usr/bin/python3 main.py --mcp
