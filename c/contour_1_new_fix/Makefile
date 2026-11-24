CC ?= gcc
CFLAGS = -std=c11 -O2 -Wall -Wextra -Wpedantic -Iinclude -I../adaptive_product/third_party
LDFLAGS = -lm

ifeq ($(OS),Windows_NT)
SHARED = bin/contour_1.dll
EXE = .exe
MKBIN = if not exist bin mkdir bin
RMF = del /q
else
SHARED = bin/libcontour_1.so
EXE =
CFLAGS += -fPIC
MKBIN = mkdir -p bin
RMF = rm -f
endif

CORE_SRC = \
	src/config.c \
	src/assess.c \
	src/select.c \
	src/selector_tree.c \
	src/routes.c \
	src/pipeline.c \
	src/names.c \
	src/timing.c

LIB_SRC = $(CORE_SRC) src/io_stb.c

CORE_OBJ = $(CORE_SRC:.c=.o)
LIB_OBJ = $(LIB_SRC:.c=.o)
LIB = contour_1.a

.PHONY: all clean bench enhance test shared

all: $(LIB) $(SHARED) bin/bench_assess$(EXE) bin/ad_enhance$(EXE) bin/test_assess$(EXE)

shared: $(SHARED)

bin/.dir:
	$(MKBIN)
	echo ok > bin/.dir

$(LIB): $(LIB_OBJ)
	ar rcs $@ $(LIB_OBJ)

src/%.o: src/%.c include/adaptive.h
	$(CC) $(CFLAGS) -c $< -o $@

$(SHARED): $(CORE_OBJ) src/pyapi.o | bin/.dir
	$(CC) -shared -O2 -o $@ $(CORE_OBJ) src/pyapi.o $(LDFLAGS)

bin/bench_assess$(EXE): tests/bench_assess.c $(LIB) | bin/.dir
	$(CC) $(CFLAGS) $< -o $@ $(LIB) $(LDFLAGS)

bin/ad_enhance$(EXE): apps/ad_enhance.c $(LIB) | bin/.dir
	$(CC) $(CFLAGS) $< -o $@ $(LIB) $(LDFLAGS)

bin/test_assess$(EXE): tests/test_assess.c $(LIB) | bin/.dir
	$(CC) $(CFLAGS) $< -o $@ $(LIB) $(LDFLAGS)

bench: bin/bench_assess$(EXE)
	./bin/bench_assess --iters 200

test: bin/test_assess$(EXE)
	./bin/test_assess

enhance: bin/ad_enhance$(EXE)

clean:
ifeq ($(OS),Windows_NT)
	$(RMF) $(subst /,\,$(LIB_OBJ) src/pyapi.o $(LIB))
else
	$(RMF) $(LIB_OBJ) src/pyapi.o $(LIB)
endif
