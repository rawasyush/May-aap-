[app]
title = My Business App
package.name = businessapp
package.domain = org.test
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 0.1

requirements = python3, kivy==2.3.0, pyzipper, pycryptodome

android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
orientation = portrait
fullscreen = 1

# 🌟 यह लाइन सबसे महत्वपूर्ण है, इससे लाइसेंस एरर नहीं आएगा
android.accept_sdk_license = True

android.archs = arm64-v8a
android.allow_backup = True
