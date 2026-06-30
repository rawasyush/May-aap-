[app]
title = My Business App
package.name = businessapp
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1

# ⚠️ pyzipper और उसकी डिपेंडेंसी (pycryptodome) को शामिल किया गया है
requirements = python3, kivy, pyzipper, pycryptodome, requests, urllib3

# ⚠️ फाइल अपलोड, ज़िपिंग और इंटरनेट के लिए ज़रूरी परमिशन
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

orientation = portrait
fullscreen = 1
android.archs = arm64-v8a
