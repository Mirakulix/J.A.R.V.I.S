#!/bin/bash
# Cleanup temporary data older than 7 days
find /var/lib/postgresql/data -name "*.tmp" -mtime +7 -delete
echo "Temporary data cleanup completed"
