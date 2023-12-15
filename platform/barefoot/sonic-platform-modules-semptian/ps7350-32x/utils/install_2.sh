#!/bin/bash

export EXTRA_KO_DIR=/lib/modules/`uname -r`/extra

sleep 10
modprobe i2c_mux
modprobe i2c_dev

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

mgadaptername='AST i2c bit bus'
ast_num=0
for i in `eval echo {0..5}`;do
	dir=/sys/bus/i2c/devices/i2c-$i
	echo "start $dir "
	if [ -d $dir ];then
		adaptername=`cat /sys/bus/i2c/devices/i2c-$i/name`
		echo "bus:i2c-$i name:$adaptername"
		if [[ $adaptername == "AST i2c bit bus" ]];then
		    echo "sys i2c num $num"
		    ast_num=$i
		    break
		fi	
	fi
done

echo "sys i2c num $num"
echo "ast module i2c num $ast_num"
if [ $ast_num -gt $num ];then
    echo "ast module i2c num $ast_num is greater than cpld mg I2C adapter $num"
    rmmod ast
	rmmod mg_cpld
	rmmod mg_cpld_adapter
	modprobe ast
fi

#----------------------------------------------------
#added
rv=`lsmod |grep adl-bmc.ko`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/adl-bmc.ko
else
	echo "[INFO] adl-bmc File exsit"
fi

rv=`lsmod |grep adl-bmc-hwmon.ko `
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/adl-bmc-hwmon.ko 
else
	echo "[INFO] adl-bmc-hwmon File exsit"
fi

rv=`lsmod |grep adl-bmc-boardinfo.ko `
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/adl-bmc-boardinfo.ko 
else
	echo "[INFO] adl-bmc-boardinfo File exsit"
fi
#----------------------------------------------------


rv=`lsmod |grep ^mg_cpld_adapter`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/mg_cpld_adapter.ko 
else
	echo "[INFO] Control Cpld Adapter File exsit"
fi

rv=`lsmod |grep ^cpld_simulate_pca`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/cpld_simulate_pca.ko
else
	echo "[INFO] CPLD Simulate mux i2c File exsit"
fi
#insmod ${EXTRA_KO_DIR}/fan_cpld.ko 


rv=`lsmod |grep ^port_cpld`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/port_cpld.ko
else
	echo "[INFO] Port cpld File exsit"
fi

rv=` lsmod |grep ^pca9548 | awk -F " " '{ print $1 }' |grep ^pca9548$`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/pca9548.ko
else
	echo "[INFO] Pca9548 File exsit"
fi

rv=`lsmod |grep ^mg_cpld | awk -F " " '{ print $1 }' |grep ^mg_cpld$`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/mg_cpld.ko
else
	echo "[INFO] mg cpld File exsit"
fi

rv=`lsmod |grep xdpe12284`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/xdpe12284.ko
else
	echo "[INFO] Cpld i2c xdpe12284 File exsit"
fi

rv=`lsmod |grep lm96080`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/lm96080.ko  mod_param_ott_vol=0
else
	echo "[INFO] Cpld i2c lm96080 File exsit"
fi

rv=`lsmod |grep cpld_i2c_eeprom`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/cpld_i2c_eeprom.ko
else
	echo "[INFO] Cpld i2c eeprom File exsit"
fi

rv=`lsmod |grep cpld_i2c_crps`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/cpld_i2c_crps.ko
else
	echo "[INFO] Cpld i2c crps File exsit"
fi

#added
rv=`lsmod |grep cpld_psu_ym2651y`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/cpld_psu_ym2651y.ko   mod_param_ott_psu=0
else
	echo "[INFO] cpld_psu_ym2651y File exsit"
fi

rv=`lsmod |grep temp -w`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/temp.ko  mod_param_ott_temp=0
else
	echo "[INFO] temp File exsit"
fi
 
#insmod ${EXTRA_KO_DIR}/lm96080.ko 
rv=`lsmod |grep qsfp28_port`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/qsfp28_port.ko
else
	echo "[INFO] Qsfp port File exsit"
fi





#mg cpld simulate pca9548  i2c 3-10
i2c_dev_path=/sys/bus/i2c/devices
dir=${i2c_dev_path}/i2c-$num/$num-0010
if [ ! -d $dir ];then
	echo cpld_sim_pca9548 0x10 >/sys/bus/i2c/devices/i2c-$num/new_device
fi


# simulate cpld channel 0 pca9548  i2c 11-18
adapter_id=$[num+1]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0074
if [ ! -d $dir ];then
	echo cpld_pca9548 0x74  > /sys/bus/i2c/devices/i2c-$((num+1))/new_device
fi 


#channel 1 - 6 reserved

#channel 7 for mg cpld itself
adapter_id=$[num+8]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0018
if [ ! -d $dir ];then
	echo xc3200an_mg_cpld 0x18 >/sys/bus/i2c/devices/i2c-$adapter_id/new_device
fi	


#channel 0 xdpe12284
adapter_id=$[num+9]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0028
if [ ! -d $dir ];then
	echo cpld_i2c_xdpe12284 0x58 >/sys/bus/i2c/devices/i2c-$adapter_id/new_device 
fi

#channel 1 reserved

#channel 2 lm96080
adapter_id=$[num+11]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0028
if [ ! -d $dir ];then
	echo cpld_i2c_lm96080 0x28 >/sys/bus/i2c/devices/i2c-$adapter_id/new_device 
fi

#channel 3 eeprom
adapter_id=$[num+12]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0053
if [ ! -d $dir ];then
	echo eeprom 0x53 >/sys/bus/i2c/devices/i2c-$adapter_id/new_device 
fi

#channel 4 barefoot
#channel 5 lmk03318

#channel 6 tmp411
adapter_id=$[num+15]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-004d
if [ ! -d $dir ];then
	echo cpld_i2c_tmp411 0x4d > /sys/bus/i2c/devices/i2c-$adapter_id/new_device
fi

#channel 7 crps
adapter_id=$[num+16]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-005a
if [ ! -d $dir ];then
	echo cpld_i2c_crps_0 0x5a >/sys/bus/i2c/devices/i2c-$adapter_id/new_device
fi
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-005b
if [ ! -d $dir ];then
	echo cpld_i2c_crps_1 0x5b >/sys/bus/i2c/devices/i2c-$adapter_id/new_device
fi


#num+17 i2c-19
rv=`lsmod |grep ^i2c_adapter1`
if [ "$rv" = "" ];then
	insmod ${EXTRA_KO_DIR}/i2c_adapter1.ko 
else
	echo "[INFO] Control Cpld sfp Adapter File exsit"
fi

#port cpld
adapter_id=$[num+17]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0011
echo $dir
if [ ! -d $dir ];then
	echo xc3400an_port_cpld 0x11 >/sys/bus/i2c/devices/i2c-$adapter_id/new_device 
fi

#port cpld pca9548 and port_info i2c 20...23
adapter_id=$[num+17]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0077
if [ ! -d $dir ];then
	echo cpld_pca9550 0x77  > /sys/bus/i2c/devices/i2c-$adapter_id/new_device 
fi


adapter_id=$[num+18]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0070
if [ ! -d $dir ];then
	echo cpld_pca9549 0x70  > /sys/bus/i2c/devices/i2c-$adapter_id/new_device 
fi

#i2c  27...34  adapter
adapter_id=$[num+19]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0071
if [ ! -d $dir ];then
	echo cpld_pca9549 0x71  > /sys/bus/i2c/devices/i2c-$adapter_id/new_device 
fi

#i2c  35...42  adapter
adapter_id=$[num+20]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0072
if [ ! -d $dir ];then
	echo cpld_pca9549 0x72  > /sys/bus/i2c/devices/i2c-$adapter_id/new_device
fi

adapter_id=$[num+21]
dir=${i2c_dev_path}/i2c-$adapter_id/$adapter_id-0073
if [ ! -d $dir ];then
	echo cpld_pca9549 0x73  > /sys/bus/i2c/devices/i2c-$adapter_id/new_device
fi

#for i in {41..48};do
for i in `eval echo {$[num+22]..$[num+53]}`;do
	dir=${i2c_dev_path}/i2c-$i/$i-0050
	if [ ! -d $dir ];then
		echo cpld_i2c_qsfp28 0x50  > /sys/bus/i2c/devices/i2c-$i/new_device
	fi
done


