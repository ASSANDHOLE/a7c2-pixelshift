/* Fixed C2 2.01 offset writer, inverse and separate snapshot finalizer.
 * Adapted from QAQLeonard/a7c2-fl23-research camera_runtime/native/installer.c
 * (782785641ca9f8b984940c7274b48706219e0da4, MIT; notice in package).
 * No shell, raw flash, calibration writes, capture command or memory writes.
 */
typedef unsigned long long u64;typedef long long i64;typedef unsigned int u32;typedef unsigned char u8;
#ifdef HOST_TEST
#include "persistent_test_abi.h"
static i64 (*dispatch)(i64,i64,i64,i64,i64,i64,i64);
#define sc(a,b,c,d,e,f,g) dispatch(a,b,c,d,e,f,g)
#else
#include "a7c2_linux_abi.h"
static i64 sc(i64 n,i64 a,i64 b,i64 c,i64 d,i64 e,i64 f){
 register i64 x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc 0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
#endif
#define REQUEST "/tmp/jiritsu/a7c2.persistent.request"
#define RESULT "/tmp/jiritsu/a7c2.persistent.result"
#define STAGING "/tmp/jiritsu/libJit.so"
static int same(const void*a,const void*b,u32 n){const u8*x=a,*y=b;for(u32 i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
static void copy(void*a,const void*b,u32 n){u8*x=a;const u8*y=b;for(u32 i=0;i<n;i++)x[i]=y[i];}
static void zero(void*a,u32 n){u8*x=a;for(u32 i=0;i<n;i++)x[i]=0;}
static i64 op(const char*p,i64 flags){return sc(56,-100,(i64)p,flags,0600,0,0);}
static i64 closefd(i64*fd){if(*fd<0)return 0;i64 s=sc(57,*fd,0,0,0,0,0);*fd=-1;return s;}
struct Window{u64 offset;u32 length,chip;const u8*before,*after;};
#include "persistent_manifest.h"
#include "sha256.h"
struct Stat{u64 dev,ino;u32 mode,nlink,uid,gid;u64 rdev,pad1;i64 size;u32 blksize,pad2;u64 blocks,rest[7];};
struct Request{u8 magic[8];u32 version,action;u8 nonce[16];};
struct Report{u8 magic[8];u32 version,action;u8 nonce[16];i64 status,rollback,readonly,cleanup;u64 pid,base;
 u32 phase,writes,writebytes,model,mode,cache,loaded,mutated,before_state[2],after_state[2];
 u8 before_hash[2][32],after_hash[2][32],boot[40];i64 drop_result,mode_result,log_result;u32 flags,image_mode;
 i64 unlink_helper,unlink_request,directory_open,directory_sync,directory_close;};
_Static_assert(sizeof(struct Stat)==128&&sizeof(struct Request)==32&&sizeof(struct Report)==368,"wire ABI");
static struct Request req;static struct Report r;static struct Stat initial[2];
static i64 fd[2];static int writable;static u8 buffer[65536],normal[65536],text[32768],maps_text[524288];
static u32 maplen;static const char*path(u32 i){return i?"/cp/cpapp-b.bin":"/usr/lib/appFw.so";}
static i64 exact(i64 file,void*data,u32 n,u64 off,int write,int sequential){u32 done=0,retries=0;
 while(done<n){i64 v=sc(sequential?(write?64:63):(write?68:67),file,(i64)((u8*)data+done),n-done,off+done,0,0);
  if(v==-4&&retries++<3)continue;if(v<=0||(u64)v>n-done)return v<0?v:-5;done+=(u32)v;}return 0;}
static i64 readall(const char*p,u8*out,u32 cap){i64 file=op(p,0);if(file<0)return file;u32 used=0,retries=0;i64 s=0;
 while(used<cap){i64 n=sc(63,file,(i64)(out+used),cap-used,0,0,0);if(n==-4&&retries++<3)continue;if(n<0){s=n;break;}if(!n){s=used;break;}if((u64)n>cap-used){s=-5;break;}used+=n;if(used==cap)s=-75;}
 i64 c=closefd(&file);return c?c:s;}
/* Parser derived verbatim except buffer/base names from the reviewed local
 * restart observer; supports named segments plus anonymous readable BSS. */
#include "persistent_maps.inc"
static i64 off_guard(void){i64 n=readall("/proc/self/maps",maps_text,sizeof(maps_text));if(n<0)return n;maplen=n;if(!parse_maps())return -100;
 i64 f=op("/proc/self/mem",0);if(f<0)return f;
 const u64 offsets[]={0x5bc35b0,0x7e6f078,0x88991a0};const u32 sizes[]={4,4,1};u32*dest[]={&r.model,&r.mode,&r.cache};i64 s=0;
 for(u32 i=0;i<3&&!s;i++){*dest[i]=0;u64 a=r.base+offsets[i];if(a<r.base||!readable(a,sizes[i]))s=-14;else s=exact(f,dest[i],sizes[i],a,0,0);}
 if(!s&&(r.model!=16||r.mode||r.cache))s=-101;
 u32 stock=1,candidate=1;
 for(u32 i=0;i<loaded_count&&!s;i++){u8 got[8],a[8],b[8];const struct Loaded*v=&loaded_fields[i];u64 at=r.base+v->rva;
  if(!readable(at,v->n)){s=-14;break;}s=exact(f,got,v->n,at,0,0);if(s)break;
  if(v->pointer){u64 x=r.base+v->stock,y=r.base+v->candidate;copy(a,&x,8);copy(b,&y,8);}else{copy(a,&v->stock,v->n);copy(b,&v->candidate,v->n);}
  stock&=same(got,a,v->n);candidate&=same(got,b,v->n);}
 r.loaded=stock?1:candidate?2:3;
 /* Each edited AP data page must be MAP_PRIVATE and contain an unchanged,
  * already relocated pointer: its live page differs from the file's addend.
  * This excludes writing file-backed shared/unrelocated pointer pages. */
 for(u32 i=0;i<cow_count&&!s;i++){u64 at=r.base+cow_fields[i].rva,got=0;int private=0;
  for(u32 j=0;j<map_count;j++)if(at>=maps[j].start&&at+8<=maps[j].end&&maps[j].private_mapping)private=1;
  if(!private){s=-103;break;}s=exact(f,&got,8,at,0,0);if(!s&&got!=r.base+cow_fields[i].addend)s=-104;}
 i64 c=closefd(&f);if(c&&!s)s=c;
 if(!s){n=readall("/proc/sys/kernel/random/boot_id",r.boot,sizeof(r.boot));if(n!=37)s=-102;}return s;}
static i64 mount_state(int ro){i64 n=readall("/proc/mounts",text,sizeof(text));if(n<0)return n;
 const char a[]="/dev/nflasha15 /usr ext2 ";u32 found=0;for(u32 i=0;i+sizeof(a)+1<(u32)n;i++)if((!i||text[i-1]=='\n')&&same(text+i,a,sizeof(a)-1)){
  u32 j=i+sizeof(a)-1;if(text[j]!='r'||text[j+1]!=(ro?'o':'w')||(text[j+2]!=','&&text[j+2]!=' '))return -30;found++;}return found==1?0:-22;}
static i64 remount(int ro){i64 s=sc(40,0,(i64)"/usr",0,0xc30+(ro?1:0),0,0);return s?s:mount_state(ro);}
static i64 inspect(u32 i,int write){fd[i]=op(path(i),(write?O_RDWR:O_RDONLY)|O_NOFOLLOW);if(fd[i]<0)return fd[i];struct Stat st;i64 s=sc(80,fd[i],(i64)&st,0,0,0,0);if(s)return s;
 if((st.mode&0170000)!=0100000||st.size!=(i64)file_sizes[i])return -22;
 if(write){if(st.dev!=initial[i].dev||st.ino!=initial[i].ino)return -116;}else initial[i]=st;return 0;}
/* state 1 stock, 2 candidate, 3 owned partial. Unknown data always refuses. */
static i64 identify(u32 chip,u8*out,u32*state){SHA256 h;sha_init(&h);int stock=1,candidate=1,owned=1;
 /* The host has just compared the complete file. Recheck fixed windows here,
  * as in the upstream BYTE_WINDOWS_ONLY build; full host readback is mandatory. */
 for(u32 k=0;k<window_count;k++){const struct Window*w=&windows[k];if(w->chip!=chip)continue;
  if(!w->length||w->length>sizeof(buffer)||w->offset>file_sizes[chip]||w->length>file_sizes[chip]-w->offset)return -22;
  i64 s=exact(fd[chip],buffer,w->length,w->offset,0,0);if(s)return s;sha_add(&h,buffer,w->length);
  stock&=same(buffer,w->before,w->length);candidate&=same(buffer,w->after,w->length);
  for(u32 j=0;j<w->length;j++)if(buffer[j]!=w->before[j]&&buffer[j]!=w->after[j])owned=0;}
 sha_end(&h,out);if(stock)*state=1;else if(candidate)*state=2;else if(owned)*state=3;else return -84;return 0;}
static i64 verify(int after){for(u32 c=0;c<2;c++){i64 s=identify(c,r.after_hash[c],&r.after_state[c]);if(s)return s;if(r.after_state[c]!=(after?2U:1U))return -84;}return 0;}
static i64 patch(int after){for(u32 order=0;order<2;order++){u32 chip=after?1-order:order;
  for(u32 k=0;k<window_count;k++){const struct Window*w=&windows[k];if(w->chip!=chip)continue;
   r.mutated=1;r.writes++;i64 s=exact(fd[chip],(void*)(after?w->after:w->before),w->length,w->offset,1,0);if(s)return s;r.writebytes+=w->length;}
  i64 s=sc(82,fd[chip],0,0,0,0,0);if(s)return s;
  s=identify(chip,r.after_hash[chip],&r.after_state[chip]);if(s)return s;if(r.after_state[chip]!=(after?2U:1U))return -84;}
 return 0;}
static i64 wbi_check(void){i64 n=readall("/sys/power/image_mode",text,32);if(n!=2||!same(text,"2\n",2))return -110;
 n=readall("/sys/power/image_dev",text,32);return n==6&&same(text,"*wbi4\n",6)?0:-111;}
static void observe_snapshot(void){i64 n=readall("/sys/power/image_mode",text,32);r.image_mode=n==2&&text[0]>='0'&&text[0]<='9'&&text[1]=='\n'?text[0]-'0':0xffffffffU;
 n=readall("/sys/power/image_dev",text,32);r.flags&=~8U;if(n==6&&same(text,"*wbi4\n",6))r.flags|=8;}
static i64 set_text(const char*p,u8 v,int*accepted){*accepted=0;i64 f=op(p,1);if(f<0)return f;i64 s=sc(64,f,(i64)&v,1,0,0,0);*accepted=s==1;i64 c=closefd(&f);return s!=1?(s<0?s:-5):c;}
static i64 finalize_snapshot(void){i64 s=wbi_check();if(s)return s;i64 log=op("/dev/kmsg",O_RDONLY|O_NONBLOCK);if(log<0)return log;
 s=sc(62,log,0,2,0,0,0);if(s<0){closefd(&log);return s;}
 int dropped=0,disabled=0;r.drop_result=set_text("/sys/power/image_drop",'1',&dropped);
 /* Finish mode0 after an accepted drop even if closing its descriptor failed. */
 if(dropped){r.flags|=2;r.mode_result=set_text("/sys/power/image_mode",'0',&disabled);if(disabled)r.flags|=4;}
 i64 n=readall("/sys/power/image_mode",text,32);if(n!=2||!same(text,"0\n",2))s=-112;else s=0;
 n=readall("/sys/power/image_dev",text,32);if(n!=6||!same(text,"*wbi4\n",6))s=-111;
 int found=0;for(u32 k=0;k<32;k++){n=sc(63,log,(i64)text,sizeof(text),0,0,0);if(n==-11||!n)break;if(n<0){r.log_result=n;break;}for(u32 j=0;j+11<=(u32)n;j++)if(same(text+j,"dropped wbi",11))found=1;}
 i64 c=closefd(&log);if(c)r.log_result=c;if(!found&&!r.log_result)r.log_result=-61;
 if(!s&&(!dropped||!disabled||r.drop_result||r.mode_result||r.log_result))s=-113;return s;}
static void work(void){i64 q=op(REQUEST,0);if(q<0){r.status=q;return;}r.status=exact(q,&req,sizeof(req),0,0,0);u8 x;i64 eof=sc(67,q,(i64)&x,1,sizeof(req),0,0),c=closefd(&q);
 if(r.status||eof||c||!same(req.magic,"A7PWQ001",8)||req.version!=1||req.action>3){r.status=-120;return;}
 u32 any=0;for(u32 i=0;i<16;i++)any|=req.nonce[i];if(!any){r.status=-120;return;}r.action=req.action;copy(r.nonce,req.nonce,16);
 r.unlink_helper=sc(35,AT_FDCWD,(i64)STAGING,0,0,0,0);r.cleanup=r.unlink_helper;
 if(!r.cleanup){r.unlink_request=sc(35,AT_FDCWD,(i64)REQUEST,0,0,0,0);r.cleanup=r.unlink_request;}
 q=op("/tmp/jiritsu",O_RDONLY|O_DIRECTORY);r.directory_open=q;
 if(q<0)r.cleanup=q;else{r.directory_sync=sc(82,q,0,0,0,0,0);if(r.directory_sync)r.cleanup=r.directory_sync;
  r.directory_close=closefd(&q);if(r.directory_close)r.cleanup=r.directory_close;}if(r.cleanup){r.status=-121;return;}
 if(sc(175,0,0,0,0,0,0)){r.status=-13;return;}r.phase=1;r.status=off_guard();if(r.status)return;
 r.status=mount_state(1);if(r.status&&req.action==2&&!mount_state(0)){writable=1;r.status=0;}if(r.status)return;
 for(u32 i=0;i<2;i++){r.status=inspect(i,0);if(r.status)return;r.status=identify(i,r.before_hash[i],&r.before_state[i]);if(r.status)return;}
 r.phase=2;if(!req.action){r.flags|=1;return;}
 if(req.action==3){if(r.before_state[0]!=r.before_state[1]||r.before_state[0]>2){r.status=-122;return;}r.phase=7;r.status=finalize_snapshot();if(!r.status)r.flags|=1;return;}
 if(req.action==2&&r.before_state[0]==1&&r.before_state[1]==1){r.phase=6;r.flags|=1;return;}
 if(req.action==1&&(r.before_state[0]!=1||r.before_state[1]!=1)){r.status=-123;return;}
 r.status=wbi_check();if(r.status&&req.action==2){observe_snapshot();if(r.image_mode==0&&(r.flags&8))r.status=0;}if(r.status)return;
 for(u32 i=0;i<2;i++){r.status=closefd(&fd[i]);if(r.status)return;}
 writable=1;r.status=remount(0);if(r.status)return;
 for(u32 i=0;i<2;i++){r.status=inspect(i,1);if(r.status)return;u8 hash[32];u32 state;r.status=identify(i,hash,&state);if(r.status)return;if(!same(hash,r.before_hash[i],32)){r.status=-124;return;}}
 r.status=off_guard();if(r.status)return;r.phase=3;r.status=patch(req.action==1);
 if(!r.status){r.phase=4;r.status=verify(req.action==1);}
 if(r.status&&r.mutated){r.phase=5;r.rollback=patch(0);if(!r.rollback)r.rollback=verify(0);return;}
 if(!r.status){r.flags|=1;r.phase=6;}
}
static void run(void){zero(&r,sizeof(r));zero(&req,sizeof(req));zero(initial,sizeof(initial));fd[0]=fd[1]=-1;writable=0;copy(r.magic,"A7PWR001",8);r.version=2;
 r.unlink_helper=r.unlink_request=r.directory_open=r.directory_sync=r.directory_close=-20000;r.pid=sc(172,0,0,0,0,0,0);work();
 for(u32 i=0;i<2;i++){i64 c=closefd(&fd[i]);if(c&&!r.status)r.status=c;}
 r.readonly=writable?remount(1):mount_state(1);if(r.readonly&&!r.status)r.status=r.readonly;observe_snapshot();
 i64 out=op(RESULT,A7C2_NEW_REPORT_FLAGS);if(out<0)return;u8 tail[24];copy(tail,"A7PWEND1",8);copy(tail+8,r.nonce,16);
 i64 s=exact(out,&r,sizeof(r),0,1,1);if(!s)s=sc(82,out,0,0,0,0,0);if(!s)s=exact(out,tail,sizeof(tail),0,1,1);if(!s)sc(82,out,0,0,0,0,0);closefd(&out);}
#ifdef HOST_TEST
__declspec(dllexport) void persistent_test_run(i64(*fn)(i64,i64,i64,i64,i64,i64,i64)){dispatch=fn;run();}
#else
__attribute__((visibility("default"))) void _init(void){run();}
#endif
