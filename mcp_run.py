import sys
import main

# حقن راية MCP برمجياً في مصفوفة النظام
sys.argv = [sys.argv[0], "--mcp"]

# استدعاء الدالة الرئيسية فوراً
main.main()
