@echo off
cd /d d:\SOLOVIBE\backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000