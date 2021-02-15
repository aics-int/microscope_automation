# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['..\\microscope_automation\\orchestrator\\microscope_automation.py'],
             binaries=[],
             datas=[],
             hiddenimports=['skimage.filters.rank.core_cy_3d'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure,
          a.zipped_data,
          cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='microscope_automation',
          debug=True,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=True,
          uac_admin=True,
          resources=['Export_ZEN_COM_Objects.exe'])
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='microscope_automation')
