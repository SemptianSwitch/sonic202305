#!/usr/bin/env bash

function bmc_usb_check()
{
  usb0=0
  num=0
  while [ $usb0 -eq 0 ]
  do
    if [ $num -gt 1 ];then
            break
    fi
        usbif=`ifconfig usb0 | awk -F":" '{print $1}'|head -n 1`
        echo $usbif 
        if [ xusb0 == x$usbif ];then
                ifconfig usb0 up
                echo "usb0 ready up\n"
				echo "usb0 ready up\n" > /dev/console
                usb0=1
        else
                echo "usb0 ready no try $num\n"
				echo "usb0 ready no try $num\n" > /dev/console
                sleep 1
                usb0=0
                let num++
        fi
  done
}

bmc_usb_check
