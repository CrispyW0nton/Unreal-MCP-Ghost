@echo off
"C:\Program Files\Epic Games\UE_5.6\Engine\Build\BatchFiles\Build.bat" CombatLevelEditor Win64 Development -Project="C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Project3\CombatTemplateLevel\CombatLevel.uproject" -WaitMutex
exit /b %ERRORLEVEL%
