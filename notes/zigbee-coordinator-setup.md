# Zigbee Coordinator Setup Guide

## Device Information

**Device**: SONOFF Dongle Lite MG21
- **USB ID**: 10c4:ea60 (Silicon Labs CP210x UART Bridge)
- **Serial Number**: 2c1766ef5fa2ef11baaf8a6661ce3355
- **Device Node (Host)**: `/dev/ttyUSB0`
- **Device Node (Inside VM)**: `/dev/ttyUSB0`

## Setup Completed

### 1. Device Passthrough Configuration ✅
- Added to Proxmox VM 100 via UI: `Add` → USB device → Selected SONOFF (10c4:ea60)
- Configuration entry in `/etc/pve/nodes/proxmox/qemu-server/100.conf`:
  ```
  usb0: host=10c4:ea60
  ```

### 2. VM Reboot ✅
- Restarted VM 100 to activate USB passthrough
- Device automatically mapped to `/dev/ttyUSB0` inside the Home Assistant OS VM

### 3. Verification ✅
- VM 100 Status: Running
- SONOFF Device: Detected on Bus 001 Device 007
- Kernel driver: cp210x (Silicon Labs CP210x UART Bridge)
- Device node created: `/dev/ttyUSB0`

---

## Configuring Zigbee in Home Assistant

### Step 1: Access Home Assistant Settings
1. Open Home Assistant UI
2. Navigate to: **Settings** → **Devices & Services**

### Step 2: Add Zigbee Integration
1. Click **Create Automation** (or search for an existing integration)
2. Search for: **"Zigbee Home Automation"** (ZHA)
3. Click to install/add

### Step 3: Select Device
1. When prompted for device path, select: `/dev/ttyUSB0`
2. For serial port speed, use default (usually 115200)
3. Complete the setup

### Step 4: Pair Devices
1. Once the integration is active, go to the integration settings
2. Click **Add device** or **Permit joins** (depends on ZHA version)
3. Enable pairing mode on your Zigbee devices
4. Devices should appear in Home Assistant

---

## Troubleshooting

### Device Not Appearing in HA
1. **Check if still on host**:
   ```bash
   lsusb | grep 10c4:ea60
   ls -la /dev/ttyUSB0
   ```

2. **Verify VM has access**:
   - Log into the HA system (SSH or console)
   - Run: `ls -la /dev/ttyUSB0`
   - Should show device with proper permissions

3. **Reload cp210x driver** (if needed):
   ```bash
   modprobe -r cp210x && sleep 1 && modprobe cp210x
   ```

### Permission Issues
- Device should have permissions: `crw-rw---- root dialout`
- If restricted, check HA user group membership

### Device Disconnects
- Check USB cable connection
- Verify no USB hubs causing instability
- Check dmesg for kernel errors: `dmesg | grep -i "cp210x\|ttyUSB"`

---

## Future Reference

### Device Detection (Host)
```bash
# Find SONOFF device
lsusb | grep -i sonoff
lsusb -d 10c4:ea60

# Check device node
ls -la /dev/ttyUSB*

# View full device details
lsusb -d 10c4:ea60 -v
```

### Check VM Status
```bash
qm status 100          # Check if running
qm config 100          # View full configuration
grep usb0 /etc/pve/nodes/proxmox/qemu-server/100.conf  # View USB passthrough
```

### Kernel Logs
```bash
dmesg | grep -i "cp210x\|ttyUSB" | tail -20
```

---

## Important Notes

- ⚠️ **Do not unplug/replug** the USB device while HA is running (will disconnect integration)
- ✅ Device persists across reboots (configured in VM config)
- ✅ Safe to restart VM 100 anytime - device will be re-recognized
- 📝 For adding/removing Zigbee devices, use HA UI (no host-level changes needed)

---

## Last Updated
- Date: April 26, 2026
- Setup Status: ✅ Complete
- Device Status: ✅ Active
