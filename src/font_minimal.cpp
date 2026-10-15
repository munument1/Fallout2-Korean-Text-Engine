// Minimal Korean adapter 1.1, MIT license. The separately supplied legacy DLL is not relicensed.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <string>
#include <vector>
#include <algorithm>
#include <cstdio>
#include <cstring>

static HMODULE self, legacy;
static unsigned cp=949;
static void (__cdecl *initFn)();
static void (__cdecl *clearFn)();
static void (__cdecl *selectFn)(int);
static void (__cdecl *outFn)(char*,int,int,unsigned char*,int);
static HDC metricDC;
static HFONT fonts[2];
static int fontId=101;
static std::wstring folder;
static std::wstring fontNames[2];
static int fontCreation=0;
static bool gameProcess=false,softGreen=false,softTextColors=false;
static void writeMem(void* dst,const void* src,size_t n) {
 DWORD old; if(!VirtualProtect(dst,n,PAGE_EXECUTE_READWRITE,&old)) throw "VirtualProtect failed";
 memcpy(dst,src,n);FlushInstructionCache(GetCurrentProcess(),dst,n);
 DWORD unused;VirtualProtect(dst,n,old,&unused);
}
static void patch(size_t off,const std::vector<unsigned char>& before,const std::vector<unsigned char>& after) {
 auto p=(unsigned char*)legacy+off;
 if(before.size()!=after.size()||memcmp(p,before.data(),before.size()))throw "legacy DLL signature mismatch";
 writeMem(p,after.data(),after.size());
}
static int nextBytes(const char* s,int remaining) {
 if(remaining>=2&&IsDBCSLeadByteEx(cp,(BYTE)*s)) {
  wchar_t w=0;
  if(MultiByteToWideChar(cp,MB_ERR_INVALID_CHARS,s,2,&w,1)==1)return 2;
 }
 return 1;
}
static std::wstring wide(const char* s,int n) {
 std::wstring out;
 if(!s||n<=0)return out;
 if((BYTE)*s==0xff){out.push_back(L'\x25cf');++s;--n;}
 for(int i=0;i<n;) {
  int k=nextBytes(s+i,n-i);wchar_t w=0;
  if(k==1&&IsDBCSLeadByteEx(cp,(BYTE)s[i])&&i+1==n)break;
  if(MultiByteToWideChar(cp,MB_ERR_INVALID_CHARS,s+i,k,&w,1)==1){
   // BIO lines retain CR from their CRLF files; GDI renders it as a missing-glyph box.
   // TextOutput is a single-line raster entry point. Multiline functions split before this point.
   if(w==L'\t')out.push_back(L' ');else if(w>=L' ')out.push_back(w);
  }
  else out.push_back(L'?');
  i+=k;
 }
 return out;
}
static BOOL WINAPI extentHook(HDC dc,LPCSTR s,int n,LPSIZE size) {
 auto w=wide(s,n);return GetTextExtentPoint32W(dc,w.c_str(),(int)w.size(),size);
}
static BOOL WINAPI outputHook(HDC dc,int x,int y,LPCSTR s,int n) {
 auto w=wide(s,n);return TextOutW(dc,x,y,w.c_str(),(int)w.size());
}
static HFONT WINAPI fontHook(int h,int w,int esc,int ori,int weight,DWORD italic,DWORD underline,
 DWORD strike,DWORD charset,DWORD outp,DWORD clip,DWORD quality,DWORD pitch,LPCSTR face) {
 auto name=fontNames[fontCreation++%2];if(name.empty())name=wide(face,(int)strlen(face));
 return CreateFontW(h,w,esc,ori,weight,italic,underline,strike,DEFAULT_CHARSET,outp,clip,NONANTIALIASED_QUALITY,pitch,name.c_str());
}
static void hookIAT(const char* name,void* replacement,HMODULE module=nullptr) {
 auto base=(BYTE*)(module?module:legacy);auto dos=(IMAGE_DOS_HEADER*)base;auto nt=(IMAGE_NT_HEADERS32*)(base+dos->e_lfanew);
 auto desc=(IMAGE_IMPORT_DESCRIPTOR*)(base+nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress);
 for(;desc->Name;++desc) {
  auto names=(IMAGE_THUNK_DATA32*)(base+desc->OriginalFirstThunk);
  auto iat=(IMAGE_THUNK_DATA32*)(base+desc->FirstThunk);
  for(;names->u1.AddressOfData;++names,++iat) {
   if(IMAGE_SNAP_BY_ORDINAL32(names->u1.Ordinal))continue;
   auto imp=(IMAGE_IMPORT_BY_NAME*)(base+names->u1.AddressOfData);
   if(!strcmp((char*)imp->Name,name)){writeMem(&iat->u1.Function,&replacement,4);return;}
  }
 }
 throw "missing legacy GDI import";
}
static int width(const char* s,int n) {
 SIZE sz={};auto w=wide(s,n);GetTextExtentPoint32W(metricDC,w.c_str(),(int)w.size(),&sz);return sz.cx;
}
static void load() {
 if(legacy)return;
 wchar_t path[MAX_PATH];GetModuleFileNameW(self,path,MAX_PATH);folder=path;
 folder.resize(folder.find_last_of(L"\\/")+1);
 for(const wchar_t* file:{L"Galmuri9.ttf",L"Galmuri11.ttf"}) {
  auto path=folder+L"fonts\\"+file;
  if(GetFileAttributesW(path.c_str())!=INVALID_FILE_ATTRIBUTES&&!AddFontResourceExW(path.c_str(),FR_PRIVATE,nullptr))throw "Cannot load private Galmuri font";
 }
 cp=GetPrivateProfileIntW(L"MISC",L"CodePage",949,(folder+L"fallout2font.ini").c_str());
 if(!cp)cp=GetACP();if(!IsValidCodePage(cp))throw "invalid configured code page";
 legacy=LoadLibraryExW((folder+L"fallout2font_legacy.dll").c_str(),nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);
 if(!legacy)throw "cannot load separately supplied fallout2font_legacy.dll";
 // Legacy DllMain reads INI beside the process executable using ANSI APIs.
 // Override the numeric configuration from the bridge's Unicode path, including in the native probe.
 auto ini=folder+L"fallout2font.ini";
 softGreen=GetPrivateProfileIntW(L"MISC",L"SoftGreen",0,ini.c_str())!=0;
 softTextColors=GetPrivateProfileIntW(L"MISC",L"SoftTextColors",0,ini.c_str())!=0;
 for(int i=0;i<2;++i){const wchar_t* section=i?L"BUTTON":L"TEXT";wchar_t face[128];
  GetPrivateProfileStringW(section,L"Name",i?L"Malgun Gothic":L"Dotum",face,128,ini.c_str());fontNames[i]=face;
  int size=GetPrivateProfileIntW(section,L"Size",i?16:11,ini.c_str());
  int weight=GetPrivateProfileIntW(section,L"Weight",400,ini.c_str());
  if(size<6||size>64||weight<0||weight>1000)throw "font configuration out of supported range";
  writeMem((BYTE*)legacy+(i?0xbd34:0xbe44),&size,4);writeMem((BYTE*)legacy+(i?0xbd38:0xbe48),&weight,4);
 }
 writeMem((BYTE*)legacy+0xbc28,&cp,4);
 int adjust=GetPrivateProfileIntW(L"MISC",L"Adjust",3,ini.c_str());writeMem((BYTE*)legacy+0xbc2c,&adjust,4);
 // Retain only the ordinary legacy raster path. The caption special case reads
 // fixed game addresses and rewrites the input using a backwards byte heuristic.
 patch(0x1315,{0xe9,0xe6,0x74,0,0},{0x56,0x8b,0x74,0x24,0x20});
 // FF is converted to a CP949 bullet before this function is called. This
 // comparison must nevertheless stop treating a normal CP949 95 lead as UI.
 patch(0x1324,{0x95},{0xff});
 hookIAT("TextOutA",(void*)&outputHook);hookIAT("GetTextExtentPoint32A",(void*)&extentHook);hookIAT("CreateFontA",(void*)&fontHook);
 #define FN(var,name) var=(decltype(var))GetProcAddress(legacy,name);if(!var)throw "missing export"
 FN(initFn,"InitFont");FN(clearFn,"ClearFont");FN(selectFn,"SelectFont");FN(outFn,"TextOutput");
 #undef FN
 // No game code or game import table is written by this adapter.
 auto game=(BYTE*)GetModuleHandleW(nullptr);
 auto nt=(IMAGE_NT_HEADERS32*)(game+((IMAGE_DOS_HEADER*)game)->e_lfanew);
 gameProcess=(uintptr_t)game==0x400000 && nt->OptionalHeader.SizeOfImage>=0x300000
     && *(DWORD*)(game+0xcaf23)==0x00225559;
}
extern "C" void __cdecl InitFont() {
 try {
  load();initFn();metricDC=CreateCompatibleDC(nullptr);
  auto ini=folder+L"fallout2font.ini";
  for(int i=0;i<2;++i){const wchar_t* sec=i?L"BUTTON":L"TEXT";wchar_t name[128];
   GetPrivateProfileStringW(sec,L"Name",i?L"Malgun Gothic":L"Dotum",name,128,ini.c_str());
   int size=GetPrivateProfileIntW(sec,L"Size",i?14:9,ini.c_str());
   int weight=GetPrivateProfileIntW(sec,L"Weight",400,ini.c_str());
   fonts[i]=CreateFontW(-size,0,0,0,weight,0,0,0,DEFAULT_CHARSET,OUT_TT_PRECIS,CLIP_DEFAULT_PRECIS,NONANTIALIASED_QUALITY,DEFAULT_PITCH,name);
  }
  SelectObject(metricDC,fonts[fontId<102?0:1]);
 }catch(const char* msg){MessageBoxA(nullptr,msg,"Korean font bridge initialization failed",MB_ICONERROR);ExitProcess(1);}
}
extern "C" void __cdecl ClearFont(){if(clearFn)clearFn();if(metricDC){DeleteDC(metricDC);metricDC=nullptr;}for(auto f:fonts)if(f)DeleteObject(f);}
extern "C" void __cdecl SelectFont(int id){fontId=id;if(selectFn)selectFn(id);if(metricDC)SelectObject(metricDC,fonts[id<102?0:1]);}
extern "C" int __cdecl GetTextWidth(const char* s){return s?width(s,(int)strlen(s)):0;}
// The Korean v28 renderer uses its normal height for Fallout 2's summary callers.
// CHT's later call-site-specific additions overflow those fixed panels with Korean fonts.
extern "C" int __cdecl GetTextHeight(){return legacy?*(int*)((BYTE*)legacy+0xbc24):0;}
static std::vector<char> mutableText(const char* s){
 std::vector<char> v;
 if(s&&*s){
  if((BYTE)*s==0xff){v.push_back((char)0xa1);v.push_back((char)0xdc);++s;}
  v.insert(v.end(),s,s+strlen(s));
 }
 v.resize(v.size()+8,0);return v;
}
static int mappedColor(int color){
 if(!gameProcess)return color;
 const auto table=(const BYTE*)0x6a38d0;
 int index=color&255;
 if(softGreen&&index==table[992])return (color&~255)|table[(6<<10)|(22<<5)|6];
 if(!softTextColors||index==0||index>=229)return color;
 // Read the base RGB palette, not the gamma/fade palette. Modify only the
 // index passed to the font rasterizer; do not write either game palette.
 const auto rgb=(const BYTE*)0x51df34+index*3;
 int r=rgb[0]>>1,g=rgb[1]>>1,b=rgb[2]>>1;
 int peak=std::max(r,std::max(g,b)),low=std::min(r,std::min(g,b));
 if(peak<16)return color; // Keep already subdued text and black shadows.
 if(peak-low>=4){
  // Mix one fifth toward the channel maximum, preserving channel order.
  r=(r*4+peak+2)/5;g=(g*4+peak+2)/5;b=(b*4+peak+2)/5;
  if(peak>22){r=(r*22+peak/2)/peak;g=(g*22+peak/2)/peak;b=(b*22+peak/2)/peak;}
 }else{
  if(peak<=25)return color;
  r=(r*25+peak/2)/peak;g=(g*25+peak/2)/peak;b=(b*25+peak/2)/peak;
 }
 return (color&~255)|table[(r<<10)|(g<<5)|b];
}
extern "C" void __cdecl TextOutput(const char* s,int w,int pitch,unsigned char* dst,int color){auto v=mutableText(s);outFn(v.data(),w,pitch,dst,mappedColor(color));}
extern "C" int __cdecl SplitText(const char* s,short* starts,short* count,int w) {
 if(!s||!starts||!count||w<=0)return 1;
 starts[0]=0;*count=1;int n=(int)strlen(s);if(n>32767)return 1;
 int start=0;
 while(start<n){int end=start,lastSpace=-1;
  while(end<n){int k=nextBytes(s+end,n-end);
   if(s[end]=='\n'||s[end]=='\r')break;
   if(width(s+start,end+k-start)>w)break;
   if(s[end]==' ')lastSpace=end;end+=k;
  }
  if(end==start)end=start+nextBytes(s+start,n-start);
  else if(end<n&&s[end]!='\r'&&s[end]!='\n'&&lastSpace>start)end=lastSpace+1;
  if(end<n&&s[end]=='\r')++end;if(end<n&&s[end]=='\n')++end;
  if(*count>=64)return 1;starts[(*count)++]=(short)end;start=end;
 }
 if(*count==1)starts[(*count)++]=0;
 return 0;
}
static int lineStep(){
 int adjust=*(int*)((BYTE*)legacy+0xbc2c);
 return std::max(1,GetTextHeight()+adjust-1);
}
extern "C" void __cdecl TextOutputL(const char* s,int w,int pitch,int* lines,unsigned char* dst,int color){
 if(!s||!lines||!dst||pitch<=0||w<=0||*lines<0)return;
 short starts[64]={},count=0;if(SplitText(s,starts,&count,w))return;
 for(int i=1;i<count;++i){
  std::string line(s+starts[i-1],starts[i]-starts[i-1]);
  TextOutput(line.c_str(),w,pitch,dst+(size_t)*lines*lineStep()*pitch,color);++*lines;
 }
}
extern "C" int __cdecl TextOutputX(const char* s,int* offset,int* rect,int pitch,unsigned char* dst,int color){
 if(!s||!rect||!dst||pitch<=0||rect[0]<0||rect[1]<0||rect[2]<=rect[0])return 0;
 int n=(int)strlen(s),initial=offset?*offset:0;
 if(initial<0||initial>n)return rect[1];
 short starts[64]={},count=0;int w=rect[2]-rect[0];
 if(SplitText(s+initial,starts,&count,w))return rect[1];
 int consumed=0;
 for(int i=1;i<count;++i){
  if(rect[1]+GetTextHeight()>rect[3])break;
  std::string line(s+initial+starts[i-1],starts[i]-starts[i-1]);
  TextOutput(line.c_str(),w,pitch,dst+(size_t)rect[1]*pitch,color);
  rect[1]+=lineStep();consumed=starts[i];
 }
 if(offset)*offset=initial+consumed<n?initial+consumed:0;
 return rect[1];
}
BOOL WINAPI DllMain(HINSTANCE h,DWORD why,LPVOID){if(why==DLL_PROCESS_ATTACH){self=h;DisableThreadLibraryCalls(h);}return TRUE;}
