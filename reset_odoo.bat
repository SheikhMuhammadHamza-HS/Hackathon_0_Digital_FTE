@echo off
echo ==========================================
echo ODOO RESET SCRIPT (Hackathon Zero)
echo ==========================================
echo.
echo [1/3] Stopping existing Odoo containers...
docker-compose -f docker-compose-odoo.yml down

echo.
echo [2/3] Wiping Odoo and Database volumes (Fresh Start)...
docker volume rm hackathon_zero_odoo_db_data
docker volume rm hackathon_zero_odoo_web_data
:: In case the prefix is different or volumes already gone:
docker volume prune -f

echo.
echo [3/3] Starting Fresh Odoo Instance...
docker-compose -f docker-compose-odoo.yml up -d

echo.
echo ==========================================
echo ODOO IS STARTING!
echo ==========================================
echo Wait 10-20 seconds, then go to: http://localhost:8069
echo.
echo MASTER PASSWORD (to create DB): admin
echo.
echo Suggested DB Name: odoo_hackathon
echo Default Admin Login: admin
echo Default Admin Pass: admin
echo ==========================================
pause