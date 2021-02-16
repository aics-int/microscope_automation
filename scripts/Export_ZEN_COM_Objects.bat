:: regScripting_Release.batecho offpushd "C:\Windows\Microsoft.NET\Framework64\v4.0.30319" 
SET dll-1="C:\Program Files\Carl Zeiss\ZEN 2\ZEN 2 (blue edition)\Zeiss.Micro.Scripting.dll"
"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe" /u /codebase /tlb %dll-1%
"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe" /codebase /tlb %dll-1%
SET dll-2="C:\Program Files\Carl Zeiss\ZEN 2\ZEN 2 (blue edition)\Zeiss.Micro.LM.Scripting.dll"
"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe" /u /codebase /tlb %dll-2%
"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\RegAsm.exe" /codebase /tlb %dll-2% popd
pause
