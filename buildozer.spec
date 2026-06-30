[app]
title = My Business App
package.name = businessapp
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1

# 🌟 यहाँ हमने python3 का सटीक वर्शन लॉक कर दिया है
requirements = python3==3.11.15, kivy==2.3.0, pyzipper, pycryptodome

android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
orientation = portrait
fullscreen = 1
android.accept_sdk_license = True

# 🌟 स्टेबल रिलीज के लिए मास्टर ब्रांच का उपयोग
p4a.branch = master

android.archs = arm64-v8a
android.allow_backup = True
