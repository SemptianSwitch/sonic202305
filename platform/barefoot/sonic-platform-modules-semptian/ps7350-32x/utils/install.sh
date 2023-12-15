#!/bin/bash
is_ps7350_1=0
hardware_inf=0
export EXTRA_KO_DIR=/lib/modules/`uname -r`/extra


rv=`lsmod |grep ^mg_cpld_adapter`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/mg_cpld_adapter.ko 
else
	echo "[INFO] Control Cpld Adapter File exsit"
fi

rv=`lsmod |grep ^mg_cpld | awk -F " " '{ print $1 }' |grep ^mg_cpld$`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/mg_cpld.ko
else
	echo "[INFO] mg cpld File exsit"
fi

for line in $(cat /proc/xc3200an_mg_cpld)
do
	#echo $line
	if [ ${line} == "Hardware_inf:" ];then
	    echo $line
            hardware_inf=1
	    continue 
	fi

	if [ $hardware_inf != 1 ];then
	    #echo $line
	    continue	
	fi

	if [ ${line} == 0xa ];then
	    echo $line
	    is_ps7350_1=1
	    break
	fi

	if [ ${line} == 0x1a ];then
	    echo $line
	    is_ps7350_1=1
	    break
	fi
	
	if [ $hardware_inf == 1 ];then
		break
	fi
done

if [ ${is_ps7350_1} == 1 ];then
	echo "is ps7350_1"
	sudo /usr/sbin/install_1.sh
else
	echo "is ps7350_2"
	sudo /usr/sbin/install_2.sh
fi

sudo /usr/sbin/pip.sh
#sudo /usr/sbin/bmc_usb_check.sh
sudo /usr/sbin/service_check.sh
sudo /usr/sbin/bmc_check.sh
