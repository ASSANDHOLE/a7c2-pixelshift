/* Compile-time target ABI, not host/x86 flag values. */
#ifndef A7C2_LINUX_ABI_H
#define A7C2_LINUX_ABI_H
#if !defined(__aarch64__) || !defined(__linux__)
#error This helper requires the AArch64 Linux ABI
#endif
#include <linux/fcntl.h>
_Static_assert(O_DIRECTORY==040000,"AArch64 directory flag changed");
_Static_assert(O_NOFOLLOW==0100000,"AArch64 no-follow flag changed");
_Static_assert(O_DIRECT==0200000,"AArch64 direct-I/O flag changed");
_Static_assert(AT_FDCWD==-100,"AArch64 cwd selector changed");
#define A7C2_NEW_REPORT_FLAGS (O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW)
_Static_assert(A7C2_NEW_REPORT_FLAGS==0x80c1,"Unexpected exclusive report flags");
#endif
