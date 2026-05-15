How to import to blender the files:

For windows:
´´´
blender --background --python-expr "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/erdoy/Blender-validation-workflow/main/import_script.py').read().decode('utf-8'))"
´´´
