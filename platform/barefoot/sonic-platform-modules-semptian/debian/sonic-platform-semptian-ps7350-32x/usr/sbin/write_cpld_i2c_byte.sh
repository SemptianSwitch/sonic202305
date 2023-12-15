#!/bin/bash

/usr/sbin/lpc write 0xa58 1 0
/usr/sbin/lpc write 0xa51 1 $1

/usr/sbin/lpc write 0xa52 1 $2
/usr/sbin/lpc write 0xa53 1 $3


/usr/sbin/lpc write 0xa50 1 0x80

/usr/sbin/lpc read 0xa57 1
