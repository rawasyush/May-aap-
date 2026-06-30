[app]
title = My Business App
package.name = businessapp
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1

# 🌟 यहाँ हमने pycryptodome और रेसिपीज को सही किया है
requirements = python3, kivy==2.3.0, pyzipper, pycryptodome

# ⚠️ फाइल हैंडलिंग के लिए आवश्यक परमिशन
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

orientation = portrait
fullscreen = 1

# 🌟 केवल arm64-v8a बिल्ड करें (इससे एरर के चांस कम हो जाते हैं)
android.archs = arm64-v8a
android.allow_backup = True

# (Ndk और Sdk को Buildozer को खुद चुनने दें, मैन्युअली नंबर न डालें)
