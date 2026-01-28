@echo off
python -m pip install --upgrade pip

:: Install Django
pip install django
@echo "django installed or upgraded succefully!"

:: Install pycryptodome for cryptographic operations
pip install pycryptodome
@echo "pycrypto installed or upgraded sucessfully!"

:: End of script
pause
