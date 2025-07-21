@echo off
REM 激活虚拟环境并运行Alpha Tools CLI
call .venv\Scripts\activate
poetry run python -m alpha_new.cli
