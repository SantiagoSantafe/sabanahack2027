import os
import sys

# Permite "import risk" al correr con python -I -m pytest (sin el cwd en sys.path).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
