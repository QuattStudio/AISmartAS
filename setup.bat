@echo off


@REM This command setup python enviroment
py -m venv .venv

@REM Activate the virtual machine
.venv\Scripts\activate

@REM Install all dependencies
pip install -r requirements.txt


@REM Deactivate the virtual machine
deactivate



