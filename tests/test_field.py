import sys; sys.path.insert(0, '.')
from src.vision.field_map import FieldMap
fm = FieldMap()
# Test midtpunkt — bør give ca. (90, 60) for en 180x120 bane
print(fm.pixel_to_cm(320, 240))