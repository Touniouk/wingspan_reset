# LEGO NXT motor project — context for continuing on Linux

## Goal
Run a LEGO Mindstorms NXT motor continuously at a set speed, standalone on the
brick (no PC tethered while it runs — ruled out USB-tethered and Bluetooth-tethered
control for this reason).

## What was tried on macOS (Apple Silicon) and why it failed
- **nxt-python over USB** (`nxt_motor_run.py`) — works in principle, needs `libusb`
  via Homebrew, but requires the Mac to stay connected via cable while running.
  Ruled out due to the no-tether requirement, not a technical failure.
- **Bluetooth via PyBluez** — dead end. PyBluez is unmaintained; its `setup.py`
  uses `use_2to3`, removed from modern `setuptools`. Does not build on Python 3.13.
- **NXC / `nbc` compiler** (`nxt_motor_run.nxc`) — the standard LEGO-NXT-community
  compiler. The macOS build is a 2011-era binary containing only PowerPC and
  32-bit Intel code ("bad CPU type" on any modern Mac, Apple Silicon included).
  No maintained source build exists for modern macOS.
- **leJOS NXJ (Java)** (`MotorRun.java`) — got furthest here:
  - Got a working Java 8 toolchain (`LEJOS_NXT_JAVA_HOME` pointed at a Corretto 8
    JDK) and successfully compiled `MotorRun.java` with `nxjc`.
  - Blocked at the firmware-flash step (`nxjflash`): its native USB driver
    (`libjfantom.jnilib`, wrapping LEGO's proprietary "Fantom" driver) is also a
    2011 PPC/i386-only binary — won't load on modern macOS.
  - leJOS's alternate USB backend (`NXTCommLibnxt` / `libnxt`) has no macOS build
    at all — its `Makefile` only targets Linux (`libjlibnxt.so`, links `-lusb`,
    ships `udev` rules).

**Bottom line: this is a macOS-specific dead end.** All the NXT-era tooling
(2006–2012) only ships working binaries for Linux/Windows/old macOS — nothing
runs on modern macOS (particularly Apple Silicon).

## Recommended path on Linux
`nbc` (the NXC compiler) is a standard Ubuntu/Debian package:
```bash
sudo apt install nbc
```
Then compile + upload the existing `.nxc` file over USB in one step:
```bash
nbc -d nxt_motor_run.nxc
```
This should avoid every problem hit on macOS — Linux is nbc's primary supported
platform and the package is natively built, no architecture mismatches.

## Files in this project directory to bring over
- `nxt_motor_run.nxc` — the NXC program to compile/upload (this is the one to use
  on Linux). Content:
  ```c
  #define MOTOR_PORT OUT_A   // OUT_A, OUT_B, or OUT_C
  #define SPEED 75           // -100 (full reverse) to 100 (full forward)

  task main()
  {
      OnFwd(MOTOR_PORT, SPEED);
      while (true)
      {
          Wait(100);
      }
  }
  ```
- `nxt_motor_run.py` — USB-tethered nxt-python fallback, works on macOS once
  `libusb` is installed, but requires a permanent cable connection.
- `MotorRun.java` — leJOS version, currently unusable on macOS due to the Fantom
  driver issue above; could be revisited on Linux if leJOS is preferred over NXC
  (Linux has working Fantom driver builds and/or `libnxt` support).

## Next step
On the Linux machine: install `nbc` via apt, confirm the NXT brick is detected
over USB (may need udev rules for LEGO's vendor ID, usually handled by the
package or documented in Ubuntu's NXT setup guides), then run
`nbc -d nxt_motor_run.nxc` to compile and upload. After that, disconnect USB and
run the program standalone from the brick's "My Files" menu.
