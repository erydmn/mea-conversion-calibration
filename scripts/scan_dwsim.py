import sys
sys.path.insert(0, ".")
import yaml
with open("config.yaml") as f: cfg = yaml.safe_load(f)
from src.dwsim_harness import DWSIMHarness
h = DWSIMHarness("Flowsheet.dwxmz", cfg, dwsim_path="C:/Users/Excalıbur/AppData/Local/DWSIM")

print("\nMaterial Streams:")
for key in h.flowsheet.GraphicObjects.Keys:
    obj = h.flowsheet.GraphicObjects[key]
    from DWSIM.Interfaces.Enums.GraphicObjects import ObjectType
    if obj.ObjectType == ObjectType.MaterialStream:
        print(obj.Tag, ":", key)

print("\nEnergy Streams:")
for key in h.flowsheet.GraphicObjects.Keys:
    obj = h.flowsheet.GraphicObjects[key]
    from DWSIM.Interfaces.Enums.GraphicObjects import ObjectType
    if obj.ObjectType == ObjectType.EnergyStream:
        print(obj.Tag, ":", key)

