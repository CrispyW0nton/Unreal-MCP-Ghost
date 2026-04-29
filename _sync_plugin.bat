@echo off
setlocal
set SRC=c:\Users\NewAdmin\Documents\GDeveloper\Workspaces\Unreal-MCP-Ghost\unreal_plugin
set DST=C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Project3\CombatTemplateLevel\Plugins\UnrealMCP

echo === Syncing plugin ===
robocopy "%SRC%\Source"         "%DST%\Source"          /MIR /NFL /NDL /NJH /NJS /NC /NS /NP
robocopy "%SRC%\Resources"      "%DST%\Resources"       /MIR /NFL /NDL /NJH /NJS /NC /NS /NP 2>NUL
copy /Y  "%SRC%\UnrealMCP.uplugin" "%DST%\UnrealMCP.uplugin" >NUL 2>&1

echo === Done ===
endlocal
