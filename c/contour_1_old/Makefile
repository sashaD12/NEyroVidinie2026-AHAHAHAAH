CC ?= gcc
CFLAGS = -std=c11 -O2 -Wall -Wextra -Wpedantic -Iinclude -I../adaptive_product/third_party
LDFLAGS = -lm

LIB_SRC = \
	src/config.c \
	src/assess.c \
	src/decide.c \
	src/routes.c \
	src/pipeline.c \
	src/timing.c \
	src/io_stb.c

LIB_OBJ = $(LIB_SRC:.c=.o)
LIB = contour_1.a

.PHONY: all clean bench enhance

all: $(LIB) bin/bench_assess bin/ad_enhance

bin:
	mkdir -p bin

$(LIB): $(LIB_OBJ)
	ar rcs $@ $(LIB_OBJ)

src/%.o: src/%.c include/adaptive.h
	$(CC) $(CFLAGS) -c $< -o $@

bin/bench_assess: tests/bench_assess.c $(LIB) | bin
	$(CC) $(CFLAGS) $< -o $@ $(LIB) $(LDFLAGS)

bin/ad_enhance: apps/ad_enhance.c $(LIB) | bin
	$(CC) $(CFLAGS) $< -o $@ $(LIB) $(LDFLAGS)

bench: bin/bench_assess
	./bin/bench_assess --iters 200

enhance: bin/ad_enhance

clean:
	rm -f $(LIB_OBJ) $(LIB) bin/bench_assess bin/ad_enhance
