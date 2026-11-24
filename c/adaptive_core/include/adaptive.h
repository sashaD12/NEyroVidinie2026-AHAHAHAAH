#ifndef ADAPTIVE_H              // якщо цей файл ще не підключали — йдемо далі
#define ADAPTIVE_H              // помічаємо: adaptive.h уже підключений (анти-дубль)

#include <stdint.h>             // підтягуємо типи uint8_t / uint16_t / uint32_t

#ifndef AD_BUDGET               // якщо AD_BUDGET ще не задали ззовні
#define AD_BUDGET 5             // скільки НАЙДЕШЕВШИХ кадрів тримаємо на ремонт
#endif                          // кінець перевірки AD_BUDGET

#define AD_ROUTE_COUNT 2        // зараз 2 маршрути: NONE і DEOVER

typedef enum AdRoute {          // перелік можливих рішень по кадру
  AD_ROUTE_NONE = 0,            // 0 = кадр ок / не беремо в ремонт
  AD_ROUTE_DEOVER = 1           // 1 = кандидат на дешеве зняття засвіту
} AdRoute;                      // коротке ім'я типу: AdRoute

typedef struct AdFrame {        // опис одного сірого кадра
  uint8_t* data;                // вказівник на пікселі (пам'ять не наша)
  uint16_t width;               // ширина кадра в пікселях
  uint16_t height;              // висота кадра в пікселях
  uint16_t stride;              // скільки байт займає один рядок
} AdFrame;                      // коротке ім'я типу: AdFrame

typedef struct AdDegrade {      // виміри пошкодження (поки лише засвіт)
  float overexp;                // сила засвіту від 0 (немає) до 1 (дуже сильно)
} AdDegrade;                    // коротке ім'я типу: AdDegrade

typedef struct AdDecision {     // повна відповідь алгоритму по кадру
  AdRoute route;                // який маршрут обрали
  float health;                 // наскільки кадр «здоровий» (1 - damage)
  float damage;                 // наскільки пошкоджений (= overexp)
  float repair_cost;            // ціна ремонту: чим МЕНША — тим краще для відбору
  AdDegrade degrade;            // сирі числа вимірів
} AdDecision;                   // коротке ім'я типу: AdDecision

typedef struct AdConfig {       // налаштування порогів і цін
  float overexp_tau;            // нижче цього — кадр майже цілий, НЕ чинимо
  float cost_base;              // базова ціна маршруту DEOVER
  float cost_per_damage;        // націнка ціни за силу пошкодження (мега-засвіт = дорожче)
} AdConfig;                     // коротке ім'я типу: AdConfig

typedef struct AdCandidate {    // один слот у корзині НАЙДЕШЕВШИХ на ремонт
  uint32_t frame_id;            // номер кадра
  float repair_cost;            // його ціна ремонту (менша = пріоритетніша)
  AdRoute route;                // який ремонт йому призначили
  uint8_t used;                 // 1 = слот зайнятий, 0 = порожній
} AdCandidate;                  // коротке ім'я типу: AdCandidate

typedef struct AdBudget {       // корзина з AD_BUDGET найдешевших кандидатів
  AdCandidate slots[AD_BUDGET]; // масив слотів (без malloc)
  uint8_t count;                // скільки слотів зараз зайнято
} AdBudget;                     // коротке ім'я типу: AdBudget

void ad_config_default(AdConfig* cfg); // заповнити cfg значеннями за замовчуванням
AdDecision ad_decide(const AdFrame* frame, const AdConfig* cfg, float overexp_ready); // вирішити: чинити чи ні

void ad_budget_reset(AdBudget* budget); // очистити корзину
void ad_budget_offer(AdBudget* budget, uint32_t frame_id, const AdDecision* decision); // запропонувати кадр у топ-дешевих
int ad_budget_contains(const AdBudget* budget, uint32_t frame_id); // чи є кадр у корзині (1/0)

#endif                          // кінець захисту ADAPTIVE_H
