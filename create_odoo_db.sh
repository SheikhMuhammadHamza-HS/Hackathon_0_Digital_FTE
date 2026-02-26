#!/bin/bash
# Create Odoo database with demo data

docker exec odoo odoo -d hackathon_zero \
  --db_user=odoo \
  --db_password=odoo \
  --db_host=db \
  --db_port=5432 \
  --without-demo=all \
  --demo \
  --stop-after-init