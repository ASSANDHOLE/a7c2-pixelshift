# Tested environment and scope

**All reported physical camera experiments were conducted by one owner, with
one A7C II and one Windows PC.** This is not multi-host, cross-platform or
cross-body validation. Successful offline reproduction adds evidence for the
byte-generation process; it does not expand that physical test population.

The compact host configuration recorded for the current reproduction checks is:

| Item | Recorded configuration |
| --- | --- |
| Host platform | Windows x64; reported kernel build **10.0.26300.9974**, display version **26H2** |
| Shell for current offline checks | PowerShell **7.6.9** |
| Python | **3.12.14**, 64-bit Windows runtime |
| Native compiler | **Zig 0.13.0**, targeting AArch64 Linux; Windows x64 DLL for syscall fixtures |
| Offline native test dependencies | **pyelftools 0.33**, **Unicorn 2.1.4** |
| Historical USB setup | WinUSB assigned to the C2 normal/service interfaces on this PC; PyUSB **1.3.1** and libusb-package **1.0.30.0** |
| Camera | One ILCE-7CM2, firmware **2.01**; final coefficient choice inferred/tuned on that body |

The OS/shell entries are the current host snapshot, not proof that the identical
Windows build was present for every earlier capture or installation. The USB
entry describes the historical working setup; no new USB detection or driver
query was performed for this export. The offline builder itself needs no driver.

The optional compiler encountered a cache-write failure in the agent's restricted
filesystem layer. It succeeded through the platform's approved local-execution
permission flow. That is an execution-environment observation, not a requirement
to disable antivirus, change camera drivers or run all commands as administrator.

No computer name, account name, personal absolute path, hardware serial, UUID,
network address or camera identity is published here. A CPU/GPU/memory inventory
is omitted because it is not needed to describe this tested software path.
The older complete software dependency record remains in
[environment.json](../evidence/environment.json), with no private identifiers.

Other Windows builds, USB setups, macOS/Linux hosts and camera bodies may require
adaptation and have not been physically validated by this project. The camera
trial's approximate **21 °C / 50% RH**, fixed/manual focus and other photographic
conditions are recorded separately in [LONG_SERIES.md](LONG_SERIES.md); there is
no environmental qualification across temperatures or humidity levels.
