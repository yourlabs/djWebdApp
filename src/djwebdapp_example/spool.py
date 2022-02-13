# you could also run ./manage.py spool continuously
spooler = Spooler()
while spooler.spool_until_empty():
    continue
