@echo off
rem Flowise 启动脚本：使用本目录便携版 Node 24，绕过 oclif 直启服务
rem 数据目录重定向到 Flowise-main\.flowise（数据库/密钥/日志/上传文件）
title Flowise
set "PATH=%~dp0node-v24.15.0-win-x64;%PATH%"
cd /d "%~dp0Flowise-main"
node start-flowise.cjs
pause
