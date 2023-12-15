#!/usr/bin/env bash

function bmc_ready_check()
{
  bmc=0
  num=0
  rm /dev/ipmi0 2> /dev/null
  while [ $bmc -eq 0 ]
  do
    if [ $num -gt 100 ];then
	    break
	fi
	
	rv=`lsmod |grep ^ipmi_si | awk -F " " '{ print $1 }' |grep ^ipmi_si$`
	
	if [ "$rv" ];then
		rmmod ipmi_ssif
        rmmod acpi_ipmi
        rmmod ipmi_devintf
        rmmod ipmi_si
        rmmod ipmi_msghandler
	fi
	
	modprobe ipmi_ssif
    modprobe acpi_ipmi
    modprobe ipmi_devintf
    modprobe ipmi_si
    modprobe ipmi_msghandler
	
	if [ -c /dev/ipmi0 ];then
		echo "bmc ready ok\n"
		echo "bmc ready ok\n" > /dev/console
		bmc=1
        break
	else
		echo "bmc is not ready try $num\n"
		echo "bmc is not ready try $num\n" > /dev/console
		sleep 3
		bmc=0
		
		if [[ x"$(/bin/systemctl is-active pmon)" == x"active" ]]; then
            /bin/systemctl stop pmon
            echo "bmc is not ready, stop pmon first"
        fi
	
	    let num++
    fi	
	
  done
}

bmc_ready_check
