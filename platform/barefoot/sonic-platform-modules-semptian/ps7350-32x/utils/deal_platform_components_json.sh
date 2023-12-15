#!/bin/bash

version_key_work=("cpld1_version"  "cpld2_version" "bios_version")
firmware_key_word=("cpld1_firmware" "cpld2_firmware" "bios_firmware")


platform=`sonic-db-dump -n CONFIG_DB -k "DEVICE_METADATA*" -y | grep platform | awk -F'"' '{print $4}' `
if [ 'X'$platform = 'X' ];then
    echo "error: valiable platform is none"
    exit 1
fi

firmware_path="/usr/local/lib/firmware/${platform}/chassis1"
component_file_path="/usr/share/sonic/device/${platform}/platform_components.json"
tmp_file_path="/usr/share/sonic/device/${platform}/.platform_components.json"

if [ ! -e ${firmware_path} ];then
    echo "error: file ${firmware_path} does not exist"
    exit 1
fi

if [ ! -e ${component_file_path} ];then
    echo "error: file ${component_file_path} does not exist"
    exit 1
fi



#deal_1=1 #there is not job to do.Script could quit.
for element in ${firmware_key_word[*]}
do   
    cat ${component_file_path} | grep $element  2>/dev/null 1>&2
    deal_1=$?
    if [ ${deal_1} -eq 0 ];then
	break
    fi
done

deal_2=1 #there is not job to do.Script could quit.
for element in ${version_key_work[*]}
do   
    cat ${component_file_path} | grep $element  2>/dev/null 1>&2
    deal_2=$?
    if [ ${deal_2} -eq 0 ];then
	break
    fi
done

if [[ ${deal_1} -eq 1 && ${deal_2} -eq 1 ]];then
    echo "there is not job to do.Script could quit."
    exit 0
fi




# if file does no exist, touch it
if [ ! -e ${tmp_file_path} ];then
   touch ${tmp_file_path}
fi



mg_cpld=`cat /proc/xc3200an_mg_cpld |grep cpld_version | awk -F' ' '{printf("%d\n", $2)}' `
if [ 'X'${mg_cpld} = 'X' ];then
    echo "error: cat /proc/xc3200an_mg_cpld fail."
    exit 1
fi
    
port_cpld=`cat /proc/xc3400an_port_info_0 |grep cpld_version | awk -F' ' '{printf("%d\n", $2)}'  `
if [ 'X'${port_cpld} = 'X' ];then
    echo "error: cat /proc/xc3400an_port_info_0 fail."
    exit 1
fi

bios=`dmidecode -s bios-version `
if [ 'X'${bios} = 'X' ];then
    echo "error: dmidecode -s bios-version fail."
    exit 1
fi




sed   -e 's#"version":"cpld1_version"#"version":"'${mg_cpld}'"#'   -e 's#"version":"cpld2_version"#"version":"'${port_cpld}'"#'  -e 's#"version":"bios_version"#"version":"'${bios}'"#'   -e 's#"firmware":"cpld1_firmware"#"firmware":"'${firmware_path}'/cpld.spkg"#'    -e 's#"firmware":"cpld2_firmware"#"firmware":"'${firmware_path}'/cpld.spkg"#'    -e 's#"firmware":"bios_firmware"#"firmware":"'${firmware_path}'/bios.bin"#'  ${component_file_path} > ${tmp_file_path}


chmod 644 ${tmp_file_path}


mv ${tmp_file_path}  ${component_file_path}


