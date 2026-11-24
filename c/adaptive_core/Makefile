CC = gcc                        # який компілятор використовувати
CFLAGS = -std=c11 -O2 -Wall -Wextra -Wpedantic -Iinclude # прапорці компіляції + шлях до .h
LDFLAGS = -lm                   # лінкувати math-бібліотеку (на майбутнє)

SRC = src/metrics.c src/select.c # список .c файлів ядра
OBJ = $(SRC:.c=.o)              # ті самі файли, але з розширенням .o
LIB = adaptive_core.a           # ім'я статичної бібліотеки на виході

.PHONY: all clean               # all і clean — не імена файлів, а цілі

all: $(LIB)                     # ціль за замовчуванням: зібрати бібліотеку

$(LIB): $(OBJ)                  # бібліотека залежить від усіх .o
	ar rcs $@ $(OBJ)            # запакувати object-файли в .a

src/%.o: src/%.c include/adaptive.h # правило: як з .c зробити .o
	$(CC) $(CFLAGS) -c $< -o $@ # скомпілювати один .c у .o

clean:                          # прибрати артефакти збірки
	rm -f $(OBJ) $(LIB)         # видалити .o і .a
