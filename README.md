How to import to blender the files:

For windows:
Run in the cmd the following:

blender --background --python-expr "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/erdoy/Blender-validation-workflow/refs/heads/main/import%20from%20github%20to%20blender.py').read().decode('utf-8'))"

