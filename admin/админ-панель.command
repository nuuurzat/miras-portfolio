#!/bin/bash
# Портфолио админ-панелін іске қосу
# Қосарлап бассаңыз — админ-панель браузерде ашылады.
ADMIN_DIR="/Users/mak/Documents/projects/mac/sham/target/проект/portfolio/admin"
cd "$ADMIN_DIR"
echo "Админ-панель іске қосылуда..."
python3 admin.py &
ADMIN_PID=$!
sleep 2
open "http://127.0.0.1:8138/admin"
wait $ADMIN_PID
