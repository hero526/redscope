# DB_NODE. ROOT PRIVILEGE.

function set_counter()
{
    
    # MSR (PMU counter)
    if [ $(lsmod | grep -w msr | wc -l) -eq 0 ];then
        sudo modprobe msr
    fi
    if [ $METRIC_SPACE == "u" ];then
        sudo /usr/sbin/wrmsr -a 0x38d 0x022;
        sudo /usr/sbin/wrmsr -a 0x186 0x4281D0;
        sudo /usr/sbin/wrmsr -a 0x187 0x4282D0;
    elif [ $METRIC_SPACE == "k" ];then
        sudo /usr/sbin/wrmsr -a 0x38d 0x011;
        sudo /usr/sbin/wrmsr -a 0x186 0x4181D0;
        sudo /usr/sbin/wrmsr -a 0x187 0x4182D0;
    elif [ $METRIC_SPACE == "ku" ] || [ $METRIC_SPACE == "uk" ] || [ $METRIC_SPACE == "" ] || [ -z $METRIC_SPACE ];then
        sudo /usr/sbin/wrmsr -a 0x38d 0x033;
        sudo /usr/sbin/wrmsr -a 0x186 0x4381D0;
        sudo /usr/sbin/wrmsr -a 0x187 0x4382D0;
    fi

	# (Controller, Channel)=(0,0)
    sudo setpci -d *:6fb0 D8.l=0x400304; sudo setpci -d *:6fb0 DC.l=0x400c04;
    # (Controller, Channel)=(0,1)
    sudo setpci -d *:6fb1 D8.l=0x400304; sudo setpci -d *:6fb1 DC.l=0x400c04;
	# (Controller, Channel)=(1,0)
    sudo setpci -d *:6fd0 D8.l=0x400304; sudo setpci -d *:6fd0 DC.l=0x400c04;
	# (Controller, Channel)=(1,1)
    sudo setpci -d *:6fd1 D8.l=0x400304; sudo setpci -d *:6fd1 DC.l=0x400c04;
}

function unset_counter()
{
    # MSR (PMU counter)
    sudo /usr/sbin/wrmsr -a 0x38d 0x0;
    sudo /usr/sbin/wrmsr -a 0x186 0x0;
    sudo /usr/sbin/wrmsr -a 0x187 0x0;

	# (Controller, Channel)=(0,0)
    sudo setpci -d *:6fb0 D8.l=0x0; sudo setpci -d *:6fb0 DC.l=0x0;
	# (Controller, Channel)=(0,1)
    sudo setpci -d *:6fb1 D8.l=0x0; sudo setpci -d *:6fb1 DC.l=0x0;
	# (Controller, Channel)=(1,0)
    sudo setpci -d *:6fd0 D8.l=0x0; sudo setpci -d *:6fd0 DC.l=0x0;
	# (Controller, Channel)=(1,1)
    sudo setpci -d *:6fd1 D8.l=0x0; sudo setpci -d *:6fd1 DC.l=0x0;
}

function init_counter()
{
    # MSR (PMU counter)
    sudo /usr/sbin/wrmsr -a 0x309 0x0; sudo /usr/sbin/wrmsr -a 0x30a 0x0;
    sudo /usr/sbin/wrmsr -a 0xc1 0x0; sudo /usr/sbin/wrmsr -a 0xc2 0x0;

	# (Controller, Channel)=(0,0)
    sudo setpci -d *:6fb0 A0.l=0x0; sudo setpci -d *:6fb0 A4.l=0x0; sudo setpci -d *:6fb0 A8.l=0x0; sudo setpci -d *:6fb0 AC.l=0x0;
    # (Controller, Channel)=(0,1)
    sudo setpci -d *:6fb1 A4.l=0x0; sudo setpci -d *:6fb1 A0.l=0x0; sudo setpci -d *:6fb1 A8.l=0x0; sudo setpci -d *:6fb1 AC.l=0x0;
	# (Controller, Channel)=(1,0)
    sudo setpci -d *:6fd0 A0.l=0x0; sudo setpci -d *:6fd0 A4.l=0x0; sudo setpci -d *:6fd0 A8.l=0x0; sudo setpci -d *:6fd0 AC.l=0x0;
	# (Controller, Channel)=(1,1)
    sudo setpci -d *:6fd1 A0.l=0x0; sudo setpci -d *:6fd1 A4.l=0x0; sudo setpci -d *:6fd1 A8.l=0x0; sudo setpci -d *:6fd1 AC.l=0x0;
}