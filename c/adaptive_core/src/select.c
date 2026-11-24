#include "adaptive.h"           // підключаємо типи AdBudget / AdDecision / константи

void ad_budget_reset(AdBudget* budget) { // повністю очистити корзину найдешевших
  uint8_t i;                    // лічильник слотів у циклі
  if (budget == 0) {            // якщо вказівник порожній
    return;                     // нічого чистити
  }                             // кінець перевірки
  budget->count = 0;            // зайнятих слотів тепер 0
  for (i = 0; i < AD_BUDGET; i += 1) { // пройти всі слоти 0..AD_BUDGET-1
    budget->slots[i].frame_id = 0;     // скинути номер кадра
    budget->slots[i].repair_cost = 0.0f; // скинути ціну
    budget->slots[i].route = AD_ROUTE_NONE; // скинути маршрут
    budget->slots[i].used = 0;  // слот вільний
  }                             // кінець циклу по слотах
}                               // кінець ad_budget_reset

void ad_budget_offer(AdBudget* budget, uint32_t frame_id, const AdDecision* decision) { // запропонувати кадр у топ НАЙДЕШЕВШИХ
  uint8_t i;                    // лічильник для пошуку найдорожчого в корзині
  uint8_t most_expensive = 0;   // індекс найдорожчого слота (його викинемо, якщо новий дешевший)

  if (budget == 0 || decision == 0) { // немає корзини або рішення
    return;                     // вихід
  }                             // кінець перевірки вказівників
  if (decision->route == AD_ROUTE_NONE) { // здоровий кадр
    return;                     // у ремонтну корзину не кладемо
  }                             // кінець фільтра

  if (budget->count < AD_BUDGET) { // ще є вільне місце — просто додаємо
    AdCandidate* slot = &budget->slots[budget->count]; // наступний вільний слот
    slot->frame_id = frame_id;  // номер кадра
    slot->repair_cost = decision->repair_cost; // ціна ремонту
    slot->route = decision->route; // маршрут
    slot->used = 1;             // слот зайнятий
    budget->count = (uint8_t)(budget->count + 1); // count++
    return;                     // готово
  }                             // кінець гілки «корзина не повна»

  for (i = 1; i < AD_BUDGET; i += 1) { // корзина повна — шукаємо НАЙДОРОЖЧИЙ слот
    if (budget->slots[i].repair_cost > budget->slots[most_expensive].repair_cost) { // цей дорожчий
      most_expensive = i;       // запам'ятовуємо його індекс
    }                           // кінець порівняння
  }                             // кінець пошуку most_expensive

  if (decision->repair_cost >= budget->slots[most_expensive].repair_cost) { // новий не дешевший
    return;                     // мега-дорогий / не вигідніший — НЕ беремо
  }                             // кінець перевірки «чи новий дешевший»

  budget->slots[most_expensive].frame_id = frame_id; // замінюємо найдорожчий на дешевший
  budget->slots[most_expensive].repair_cost = decision->repair_cost; // нова (менша) ціна
  budget->slots[most_expensive].route = decision->route; // маршрут
  budget->slots[most_expensive].used = 1; // слот зайнятий
}                               // кінець ad_budget_offer

int ad_budget_contains(const AdBudget* budget, uint32_t frame_id) { // перевірити, чи кадр уже в корзині
  uint8_t i;                    // лічильник слотів
  if (budget == 0) {            // немає корзини
    return 0;                   // «не знайдено»
  }                             // кінець перевірки
  for (i = 0; i < budget->count; i += 1) { // дивимось зайняті слоти
    if (budget->slots[i].used != 0 && budget->slots[i].frame_id == frame_id) { // збіг id
      return 1;                 // знайшли
    }                           // кінець умови
  }                             // кінець циклу
  return 0;                     // не знайшли
}                               // кінець ad_budget_contains
