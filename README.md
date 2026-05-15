How to import to blender the files:

For windows:
Run in the cmd the following:

"C:\Program Files\Blender Foundation\Blender 5.1\blender" --python-expr "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/erdoy/Blender-validation-workflow/refs/heads/main/import%20from%20github%20to%20blender.py').read().decode('utf-8'))"

This is the path to your blender executable: "C:\Program Files\Blender Foundation\Blender 5.1\blender". Depending on your setup you may need to change it

In order to commit changes and delete the files from the local memory, run:

"C:\Program Files\Blender Foundation\Blender 5.1\blender" --background --python-expr "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/erdoy/Blender-validation-workflow/refs/heads/main/commit%20and%20clean.py').read().decode('utf-8'))"

IF you need to install pandas run in windows:

"C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe" -m pip install pandas --user
