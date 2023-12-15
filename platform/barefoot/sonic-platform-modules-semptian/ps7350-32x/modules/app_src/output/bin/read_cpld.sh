#!/bin/bash

#/usr/sbin/lpc write 0xa51 1 $1

#/usr/sbin/lpc write 0xa52 1 $2
#/usr/sbin/lpc write 0xa50 1 0x81

#/usr/sbin/lpc read 0xa57 1 
#/usr/sbin/lpc read 0xa56 1
#/usr/sbin/lpc read 0xa55 1
/usr/sbin/lpc write 0xa01 1 $1
/usr/sbin/lpc write 0xa00 1 0xc0
/usr/sbin/lpc read  0xa07 1
/usr/sbin/lpc read  0xa06 1

