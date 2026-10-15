#!/bin/bash
dnf update -y
dnf install -y httpd
systemctl enable --now httpd
echo "<h1>Self-Healing Server</h1><p>Status: ALIVE</p><p>Deployed via AWS CLI. Healed by Lambda.</p>" > /var/www/html/index.html