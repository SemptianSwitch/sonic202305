#!/usr/bin/env bash

#cp /usr/sbin/*.service /lib/systemd/system/  > /dev/null 2>&1
#cmd=`sudo systemctl is-enabled  ps7350-32x-monitor-watchdog.service`
#ret=`echo $cmd | awk '{print $0}'`
#if [  $ret != "enabled" ];then
#    sudo systemctl  enable   ps7350-32x-monitor-watchdog.service  
#fi

cmd=`sudo systemctl is-active  ps7350-32x-monitor-watchdog.service`
ret=`echo $cmd | awk '{print $0}'`
if [  $ret != "active"  ];then
    sudo systemctl  start     ps7350-32x-monitor-watchdog.service  
fi


#cmd=`sudo systemctl is-enabled  ps7350-32x-monitor-led.service`
#ret=`echo $cmd | awk '{print $0}'`
#if [  $ret != "enabled" ];then
#    sudo systemctl  enable   ps7350-32x-monitor-led.service 
#fi

cmd=`sudo systemctl is-active  ps7350-32x-monitor-led.service`
ret=`echo $cmd | awk '{print $0}'`
if [  $ret != "active"  ];then
    sudo systemctl  start     ps7350-32x-monitor-led.service 
fi


#cmd=`sudo systemctl is-enabled  serial-getty@ttyS1.service`
#ret=`echo $cmd | awk '{print $0}'`
#if [  $ret != "enabled" ];then
#    sudo systemctl  enable   serial-getty@ttyS1.service  
#fi

cmd=`sudo systemctl is-active  serial-getty@ttyS1.service`
ret=`echo $cmd | awk '{print $0}'`
if [  $ret != "active"  ];then
    sudo systemctl  start     serial-getty@ttyS1.service
fi


#cmd=`sudo systemctl is-enabled  ps7350-32x-monitor-usbnet.service`
#ret=`echo $cmd | awk '{print $0}'`
#if [  $ret != "enabled" ];then
#    sudo systemctl  enable   ps7350-32x-monitor-usbnet.service  
#fi

cmd=`sudo systemctl is-active  ps7350-32x-monitor-usbnet.service`
ret=`echo $cmd | awk '{print $0}'`
if [  $ret != "active"  ];then
    sudo systemctl  start     ps7350-32x-monitor-usbnet.service 
fi

cmd=`sudo systemctl is-active pmon.service`
ret=`echo $cmd | awk '{print $0}'`
if [  $ret == "active"  ];then
    echo “restart pmon service”
    sudo systemctl stop pmon.service
    sudo systemctl start  pmon.service
fi
