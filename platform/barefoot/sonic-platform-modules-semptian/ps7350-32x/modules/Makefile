#!/bin/bash

obj-m += cpld_temp.o
cpld_temp-objs := temp_device.o

obj-m += cpld_lm96080.o
cpld_lm96080-objs := cpld_i2c_lm96080.o

obj-m += mg_cpld_adapter.o
mg_cpld_adapter-objs := ddi_lpc.o  i2c-adapter_mg.o  plt_log.o

obj-m += i2c_adapter1.o
i2c_adapter1-objs := ddi_lpc1.o  i2c-adapter1_mg.o  plt_log.o

obj-m += xdpe12284.o
xdpe12284-objs := cpld_i2c_xdpe12284.o

obj-m += cpld_i2c_lmk03318.o
cpld_i2c_lmk03318-obj :=cpld_i2c_lmk03318.o

obj-m += cpld_i2c_zl8802.o
cpld_i2c_zl8802-obj :=cpld_i2c_zl8802.o

obj-m += pca9548.o
pca9548-obj := pca9548.o

obj-m += cpld_i2c_eeprom.o
cpld_i2c_eeprom-obj := cpld_i2c_eeprom.o


obj-m += tps53681.o
tps53681-obj := tps53681.o

obj-m += cpld_i2c_crps.o
i2c_crps-obj := cpld_i2c_crps.o

obj-m +=mg_cpld.o
mg_cpld-objs :=xc3200an_mg_cpld.o


obj-m += port_cpld.o
port_cpld-objs := xc3400an_port_cpld.o


obj-m += fan_cpld.o
fan_cpld-objs := xc3200an_fan_cpld.o


obj-m +=qsfp28_port.o
qsfp28_port-objs:=cpld_i2c_qsfp28.o

obj-m +=cpld_simulate_pca.o
cpld_simulate_pca-objs:=cpld_simulate_pca9548.o

#KERNELDIR ?= /lib/modules/4.19.0-16-amd64/build
KERNELDIR ?= /lib/modules/4.9.0-11-2-amd64/build

#KERNELDIR ?=/sonic/src/sonic-linux-kernel/linux-5.10.46/debian/build/build_amd64_none_amd64/
PWD       := $(shell pwd)

EXTRA_CFLAGS += -I.

all:
	$(MAKE) -C $(KERNELDIR) M=$(PWD) modules

clean:
	rm -rf *.o *.o.d  *mod.c *order *symvers *.ur-safe *.ko
	find -name *.cmd  -delete
	find -name *.o.d  -delete
	rm -rf .cache.mk 
	rm -rf .tmp_versions/
