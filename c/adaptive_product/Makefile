CC ?= gcc
CFLAGS = -std=c11 -O2 -Wall -Wextra -Wpedantic -Iinclude -Ithird_party
LDFLAGS = -lm

LIB_SRC = \
	src/config.c \
	src/assess.c \
	src/decide.c \
	src/select.c \
	src/routes.c \
	src/pipeline.c \
	src/timing.c \
	src/io_stb.c

LIB_OBJ = $(LIB_SRC:.c=.o)
LIB = libadaptive.a

.PHONY: all clean test enhance

all: $(LIB) bin/ad_enhance bin/test_core

bin:
	mkdir -p bin

$(LIB): $(LIB_OBJ)
	ar rcs $@ $(LIB_OBJ)

src/%.o: src/%.c include/adaptive.h
	$(CC) $(CFLAGS) -c $< -o $@

bin/ad_enhance: apps/ad_enhance.c $(LIB) | bin
	$(CC) $(CFLAGS) $< -o $@ $(LIB) $(LDFLAGS)

bin/test_core: tests/test_core.c $(LIB) | bin
	$(CC) $(CFLAGS) $< -o $@ $(LIB) $(LDFLAGS)

test: bin/test_core
	./bin/test_core

enhance: bin/ad_enhance

clean:
	rm -f $(LIB_OBJ) $(LIB) bin/ad_enhance bin/test_core
