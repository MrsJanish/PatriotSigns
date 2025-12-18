@echo off
echo Initializing Git Repository...
git init
git remote add origin https://github.com/MrsJanish/PatriotSigns
git add .
git commit -m "Initial commit of Patriot Intro module"
git push -u origin master
echo.
echo Deployment Complete! You can now verify on Odoo.sh.
pause
