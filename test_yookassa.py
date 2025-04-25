#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

print("Python версия:", sys.version)
print("Пути импорта Python:", sys.path)

try:
    import yookassa
    print("YooKassa успешно импортирована!")
    print("Версия YooKassa:", yookassa.__version__)
except ImportError as e:
    print("Ошибка импорта YooKassa:", str(e))
    print("Тип ошибки:", type(e).__name__)

print("\nПроверка наличия ключевых модулей:")
for module in ["requests", "urllib3", "certifi"]:
    try:
        __import__(module)
        print(f"✅ {module} - доступен")
    except ImportError:
        print(f"❌ {module} - недоступен") 