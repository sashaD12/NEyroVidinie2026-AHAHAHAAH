#define STB_IMAGE_IMPLEMENTATION
#define STB_IMAGE_WRITE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_ONLY_PNG
#define STBI_ONLY_BMP

#include "adaptive.h"

#include <ctype.h>
#include <string.h>

#include "stb_image.h"
#include "stb_image_write.h"

static int ad_ends_with_ci(const char* path, const char* ext) {
  size_t path_len;
  size_t ext_len;
  size_t i;
  if (path == 0 || ext == 0) {
    return 0;
  }
  path_len = strlen(path);
  ext_len = strlen(ext);
  if (path_len < ext_len) {
    return 0;
  }
  for (i = 0; i < ext_len; i += 1) {
    char a = (char)tolower((unsigned char)path[path_len - ext_len + i]);
    char b = (char)tolower((unsigned char)ext[i]);
    if (a != b) {
      return 0;
    }
  }
  return 1;
}

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

int ad_save_gray(const char* path, const AdFrame* frame) {
  if (path == 0 || frame == 0 || frame->data == 0) {
    return 0;
  }
  if (ad_ends_with_ci(path, ".jpg") || ad_ends_with_ci(path, ".jpeg")) {
    return stbi_write_jpg(path, frame->width, frame->height, 1, frame->data, 90) != 0;
  }
  if (ad_ends_with_ci(path, ".bmp")) {
    return stbi_write_bmp(path, frame->width, frame->height, 1, frame->data) != 0;
  }
  return stbi_write_png(path, frame->width, frame->height, 1, frame->data, frame->stride) != 0;
}

void ad_free_owned(uint8_t* owned) {
  if (owned != 0) {
    stbi_image_free(owned);
  }
}
