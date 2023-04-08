#!/bin/bash

git stash
mv $1 .
rm db.sqlite3
./manage.py migrate
./manage.py loaddata test_migration.sh
git stash apply
mv ${1##*/} $1
./manage.py migrate
