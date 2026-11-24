CC ?= gcc
CFLAGS = -std=c11 -O2 -Wall -Wextra -Wpedantic -Iinclude -I../adaptive_product/third_party
LDFLAGS = -lm

LIB_SRC = \
	src/config.c \
	src/assess.c \
	src/surf.c \
	src/timing.c \
	src/io_stb.c

LIB_OBJ = $(LIB_SRC:.c=.o)
LIB = contour_2.a

.PHONY: all clean bench

all: $(LIB) bin/bench_assess

bin:
	mkdir -p bin

$(LIB): $(LIB_OBJ)
	ar rcs $@ $(LIB_OBJ)

src/%.o: src/%.c include/adaptive.h
	$(CC) $(CFLAGS) -c $< -o $@

bin/bench_assess: tests/bench_assess.c $(LIB) | bin
	$(CC) $(CFLAGS) $< -o $@ $(LIB) $(LDFLAGS)

bench: bin/bench_assess
	./bin/bench_assess --iters 200

clean:
	rm -f $(LIB_OBJ) $(LIB) bin/bench_assess
