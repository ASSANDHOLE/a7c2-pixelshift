#define MAP_RANGE_CAPACITY 4096U
static struct Mapping{u64 start,end;u32 permissions,private_mapping;} maps[MAP_RANGE_CAPACITY];
static u32 map_count,map_line,map_app_segments,map_bases,map_parse_result;
static int hex(char c) {
    if(c>='0' && c<='9')return c-'0';
    if(c>='a' && c<='f')return c-'a'+10;
    return -1;
}
static int number(const u8 **p,const u8 *end,u64 *value) {
    u32 n=0;u64 v=0;
    while(*p<end && hex(**p)>=0) {
        if(n++==16)return 0;
        v=(v<<4)|(u32)hex(*(*p)++);
    }
    *value=v;return n!=0;
}
static int skip(const u8 **p,const u8 *end) {
    while(*p<end && **p==' ')(*p)++;
    if(*p==end)return 0;
    while(*p<end && **p!=' ')(*p)++;
    return 1;
}
static int suffix(const u8 *p,const u8 *end) {
    const char text[]="/appFw.so";if(end-p<9)return 0;
    p=end-9;for(u32 i=0;i<9;i++)if(p[i]!=(u8)text[i])return 0;
    return 1;
}
static int parse_maps(void) {
    const u8 *p=maps_text,*end=p+maplen;u32 bases=0;
    const u8 *object_path=0;u64 path_size=0;
    map_count=map_line=map_app_segments=map_bases=0;map_parse_result=0;
    while(p<end) {
        map_line++;
        const u8 *line=p;while(p<end && *p!='\n')p++;
        if(p==end){map_parse_result=2;return 0;}
        const u8 *line_end=p++;u64 start,finish,offset;
        if(!number(&line,line_end,&start)||line==line_end||*line++!='-'||
           !number(&line,line_end,&finish)||start>=finish||
           ((start|finish)&4095)||line==line_end||*line++!=' '){map_parse_result=3;return 0;}
        if(line_end-line<5){map_parse_result=4;return 0;}
        if((line[0]!='r'&&line[0]!='-')||(line[1]!='w'&&line[1]!='-')||
           (line[2]!='x'&&line[2]!='-')||(line[3]!='p'&&line[3]!='s')){map_parse_result=4;return 0;}
        int readable=*line=='r';u32 permissions=readable|(line[1]=='w'?2:0)|(line[2]=='x'?4:0);
        u32 private_mapping=line[3]=='p';line+=4;
        if(*line++!=' '||!number(&line,line_end,&offset)){map_parse_result=5;return 0;}
        if(!skip(&line,line_end)||!skip(&line,line_end)){map_parse_result=6;return 0;} /* dev, inode */
        while(line<line_end && *line==' ')line++;
        if(readable) {
            if(map_count==MAP_RANGE_CAPACITY){map_parse_result=7;return 0;}
            maps[map_count++]=(struct Mapping){start,finish,permissions,private_mapping};
        }
        if(!suffix(line,line_end))continue;
        map_app_segments++;
        if(!object_path){object_path=line;path_size=line_end-line;}
        if((u64)(line_end-line)!=path_size){map_parse_result=8;return 0;}
        for(u64 i=0;i<path_size;i++)if(line[i]!=object_path[i]){map_parse_result=8;return 0;}
        /* A named ELF guard range is valid, but never authorizes a memory read. */
        if(readable && offset==0){r.base=start;bases++;map_bases=bases;}
    }
    map_parse_result=bases==1?1:9;return bases==1;
}
static int readable(u64 address,u32 n) {
    if(address+n<address)return 0;
    for(u32 i=0;i<map_count;i++)
        if(address>=maps[i].start && address+n<=maps[i].end)return 1;
    return 0;
}
