sudo ifdown --force eth0
sleep 0.1

echo "=============================================================="
echo "lsusb:"
lsusb
echo "=============================================================="
echo "buspower file:"
cat /sys/devices/platform/bcm2708_usb/buspower
echo "busconnected file:"
cat /sys/devices/platform/bcm2708_usb/busconnected
echo "bussuspend file:"
cat /sys/devices/platform/bcm2708_usb/bussuspend

echo "=============================================================="
echo "Bus power stoping.."
echo "=============================================================="

sudo sh -c "echo 0 > /sys/devices/platform/bcm2708_usb/buspower"
sleep 4

echo "=============================================================="
echo "lsusb:"
lsusb
echo "=============================================================="
echo "buspower file:"
cat /sys/devices/platform/bcm2708_usb/buspower
echo "busconnected file:"
cat /sys/devices/platform/bcm2708_usb/busconnected
echo "bussuspend file:"
cat /sys/devices/platform/bcm2708_usb/bussuspend

echo "=============================================================="
echo "Bus power starting.."
echo "=============================================================="
sudo sh -c "echo 1 > /sys/devices/platform/bcm2708_usb/buspower"
sleep 4

echo "=============================================================="
echo "lsusb:"
lsusb
echo "=============================================================="
echo "buspower file:"
cat /sys/devices/platform/bcm2708_usb/buspower
echo "busconnected file:"
cat /sys/devices/platform/bcm2708_usb/busconnected
echo "bussuspend file:"
cat /sys/devices/platform/bcm2708_usb/bussuspend

sudo ifup --force eth0
