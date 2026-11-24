#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_ONLY_PNG
#define STBI_ONLY_BMP

#include "adaptive.h"

#include "stb_image.h"

int ad_load_gray(const char* path, AdFrame* frame, uint8_t** owned) {
  int w;
  int h;
  int comp;
  uint8_t* pixels;

  if (path == 0 || frame == 0 || owned == 0) {
    return 0;
  }

  pixels = stbi_load(path, &w, &h, &comp, 1);
  if (pixels == 0 || w <= 0 || h <= 0) {
    return 0;
  }

  frame->data = pixels;
  frame->width = (uint16_t)w;
  frame->height = (uint16_t)h;
  frame->stride = (uint16_t)w;
  *owned = pixels;
  return 1;
}

void ad_free_owned(uint8_t* owned) {
  if (owned != 0) {
    stbi_image_free(owned);
  }
}
