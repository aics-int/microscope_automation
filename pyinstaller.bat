pyinstaller --log-level WARN ^
  --resource "microscope_automation/Export_ZEN_COM_Objects.bat bat" ^
  --uac-admin ^
  --no-confirm ^
  microscope_automation\microscope_automation.py

pyinstaller --log-level WARN --resource "Export_ZEN_COM_Objects.bat" --uac-admin microscope_automation.py
70645 ERROR: resource type and/or name not specified

pyinstaller --log-level WARN --resource "Export_ZEN_COM_Objects.bat *" --uac-admin microscope_automation.py
70963 ERROR: Error while updating resources in C:\Users\fletcher.chapin\Documents\Git\microscope_automation\microscope_automation\build\microscope_automation\run.exe.7hq_uy03
from resource file C:\Users\fletcher.chapin\Documents\Git\microscope_automation\microscope_automation\Export_ZEN_COM_Objects.bat *
