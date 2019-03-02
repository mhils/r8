import os
import shutil

os.chdir(os.path.abspath(os.path.dirname(__file__)))


os.system("sphinx-build -E -b html . build index.rst")

shutil.move("build/index.html", "index.html")
shutil.rmtree("build")
