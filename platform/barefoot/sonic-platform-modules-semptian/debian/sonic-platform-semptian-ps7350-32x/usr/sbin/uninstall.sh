#!/bin/bash

export EXTRA_KO_DIR=/lib/modules/`uname -r`/extra

sleep 10

i2c_dev_path=/sys/bus/i2c/devices




num=`ls -al /sys/bus/i2c/devices | grep i2c |grep pci| wc -l`
mgadaptername='cpld mg I2C adapter'
for i in `eval echo {0..5}`;do
	dir=/sys/bus/i2c/devices/i2c-$i
	echo "start $dir "
	if [ -d $dir ];then
		adaptername=`cat /sys/bus/i2c/devices/i2c-$i/name`
		echo "bus:i2c-$i name:$adaptername"
		if [[ $adaptername == "cpld mg I2C adapter" ]];then
		    echo "sys i2c num $num"
		    num=$i
		    break
		fi	
	fi
done

if [ $i -eq 5 ];then
    echo "not find cpld mg I2C adapter $i"
    exit
fi

echo "sys i2c num $num"


##########################################################################################

sudo systemctl stop ps7350-32x-monitor-watchdog.service
sudo systemctl stop ps7350-32x-monitor-led.service
sudo systemctl stop serial-getty@ttyS1.service
sudo systemctl stop ps7350-32x-monitor-usbnet.service
