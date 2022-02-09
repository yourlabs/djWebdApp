# use local blockchain with sandbox account
from pytezos import pytezos
client = pytezos.using(
    key='edsk3gUfUPyBSfrS9CCgmCiQsTCHGkviBDusMxDJstFtojtc1zcpsh',
    shell='http://tzlocal:8732',
)
