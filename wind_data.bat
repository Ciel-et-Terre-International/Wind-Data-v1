@echo off
chcp 65001 >nul
title Wind Data - Initialisation projet
echo ==========================================
echo   Wind Data - Initialisation projet
echo ==========================================

REM Répertoire courant
echo Répertoire courant : "%CD%"

REM Vérification des bibliothèques
echo Vérification des bibliothèques essentielles...
echo Tous les modules sont disponibles.

REM Question utilisateur
set /p input="Souhaitez-vous lancer script.py ? (O/N) : "
if /i "%input%"=="O" (
    echo Lancement de script.py...
    python script.py
) else (
    echo Lancement annulé.
)

pause
