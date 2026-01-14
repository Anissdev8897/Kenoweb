@echo off
REM ============================================================
REM Script de démarrage automatique - Keno Analyzer Pro
REM Installe les dépendances et démarre l'application Flask
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo    Keno Analyzer Pro - Demarrage Automatique
echo ============================================================
echo.

REM Variables de configuration
set VENV_NAME=venv
set REQUIREMENTS_FILE=requirements.txt
set APP_DIR=src
set APP_FILE=app.py
set PORT=5000

REM Vérifier si Python est installé
echo [1/6] Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH
    echo Veuillez installer Python 3.8 ou superieur depuis https://www.python.org/
    pause
    exit /b 1
)
python --version
echo [OK] Python detecte
echo.

REM Vérifier si le fichier requirements.txt existe
if not exist "%REQUIREMENTS_FILE%" (
    echo [ERREUR] Le fichier %REQUIREMENTS_FILE% est introuvable
    pause
    exit /b 1
)
echo [OK] Fichier %REQUIREMENTS_FILE% trouve
echo.

REM Créer l'environnement virtuel s'il n'existe pas
echo [2/6] Configuration de l'environnement virtuel...
if not exist "%VENV_NAME%" (
    echo Creation de l'environnement virtuel...
    python -m venv %VENV_NAME%
    if errorlevel 1 (
        echo [ERREUR] Echec de la creation de l'environnement virtuel
        pause
        exit /b 1
    )
    echo [OK] Environnement virtuel cree
) else (
    echo [OK] Environnement virtuel deja present
)
echo.

REM Activer l'environnement virtuel
echo [3/6] Activation de l'environnement virtuel...
call %VENV_NAME%\Scripts\activate.bat
if errorlevel 1 (
    echo [ERREUR] Echec de l'activation de l'environnement virtuel
    pause
    exit /b 1
)
echo [OK] Environnement virtuel active
echo.

REM Mettre à jour pip
echo [4/6] Mise a jour de pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [ATTENTION] Echec de la mise a jour de pip, continuation...
) else (
    echo [OK] pip mis a jour
)
echo.

REM Installer les dépendances
echo [5/6] Installation des dependances depuis %REQUIREMENTS_FILE%...
echo Cela peut prendre plusieurs minutes...
python -m pip install -r %REQUIREMENTS_FILE%
if errorlevel 1 (
    echo [ERREUR] Echec de l'installation des dependances
    echo Veuillez verifier les erreurs ci-dessus
    pause
    exit /b 1
)
echo [OK] Dependances installees avec succes
echo.

REM Vérifier si le fichier .env existe
echo [6/6] Verification de la configuration...
if not exist ".env" (
    echo [ATTENTION] Le fichier .env n'existe pas
    echo Creation d'un fichier .env par defaut...
    (
        echo # Configuration de l'application Keno Analyzer Pro
        echo # Copiez ce fichier et modifiez les valeurs selon votre environnement
        echo.
        echo # Base de donnees PostgreSQL
        echo # DATABASE_URL=postgresql://user:password@localhost:5432/keno_db
        echo.
        echo # Clé secrète Flask (générez une nouvelle clé pour la production)
        echo FLASK_SECRET_KEY=keno_analyzer_pro_2024_secure_key_change_in_production
        echo.
        echo # Port de l'application
        echo PORT=%PORT%
        echo.
        echo # Configuration debug (False pour production)
        echo FLASK_ENV=development
        echo FLASK_DEBUG=True
    ) > .env
    echo [OK] Fichier .env cree avec les valeurs par defaut
    echo [ATTENTION] Veuillez configurer DATABASE_URL dans le fichier .env
) else (
    echo [OK] Fichier .env trouve
)

REM Note: Les variables d'environnement sont chargées automatiquement par python-dotenv
REM dans app.py, pas besoin de les charger manuellement ici
echo [INFO] Les variables d'environnement seront chargees automatiquement par python-dotenv

REM Vérifier si DATABASE_URL est définie
if "%DATABASE_URL%"=="" (
    echo [ATTENTION] DATABASE_URL n'est pas definie dans .env
    echo L'application va utiliser une configuration par defaut
    echo Pour utiliser PostgreSQL, configurez DATABASE_URL dans .env
)

echo.
echo ============================================================
echo    Demarrage de l'application Flask
echo ============================================================
echo.
echo Application disponible sur: http://localhost:%PORT%
echo.
echo Appuyez sur Ctrl+C pour arreter le serveur
echo.

REM Changer vers le répertoire src si nécessaire
cd /d "%APP_DIR%"

REM Démarrer l'application Flask
python %APP_FILE%

REM Si on arrive ici, l'application s'est arrêtée
echo.
echo [INFO] Application arretee
pause

