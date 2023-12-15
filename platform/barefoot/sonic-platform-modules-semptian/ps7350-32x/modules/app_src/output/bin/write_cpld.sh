#!/bin/bash

/usr/sbin/lpc write 0xa01 1 $1

/usr/sbin/lpc write 0xa02 1 $2
/usr/sbin/lpc write 0xa04 1 $3
/usr/sbin/lpc write 0xa03 1 $4

/usr/sbin/lpc write 0xa00 1 0x82

/usr/sbin/lpc read 0xa07 1
