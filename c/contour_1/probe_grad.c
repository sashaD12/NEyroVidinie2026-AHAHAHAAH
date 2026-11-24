#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_ONLY_PNG
#include "stb_image.h"
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
int main(int argc, char** argv){
  int w,h,c; unsigned char* p=stbi_load(argv[1],&w,&h,&c,1);
  if(!p) return 1;
  double ex=0,ey=0; int n=0;
  int step=8;
  for(int y=1;y<h-1;y+=step){
    for(int x=1;x<w-1;x+=step){
      int i=y*w+x;
      int gx=abs((int)p[i+1]-(int)p[i-1]);
      int gy=abs((int)p[i+w]-(int)p[i-w]);
      ex+=gx; ey+=gy; n++;
    }
  }
  double mx=ex>ey?ex:ey, mn=ex<ey?ex:ey; if(mn<1) mn=1;
  printf("%s ex=%.1f ey=%.1f ratio=%.3f sproxy=%.1f\n", argv[1], ex/n, ey/n, mx/mn, (ex+ey)/n);
  stbi_image_free(p); return 0;
}
