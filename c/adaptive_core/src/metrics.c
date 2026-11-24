#include "adaptive.h"           // підключаємо наші типи й прототипи функцій

void ad_config_default(AdConfig* cfg) { // записати дефолтні налаштування в cfg
  if (cfg == 0) {               // якщо передали порожній вказівник
    return;                     // нічого не робимо, виходімо
  }                             // кінець перевірки вказівника
  cfg->overexp_tau = 0.25f;     // ниже: кадр майже цілий → не чинимо
  cfg->cost_base = 0.08f;       // базова ціна зняття засвіту
  cfg->cost_per_damage = 1.0f;  // чим сильніший засвіт — тим ДОРОЖЧИЙ ремонт
}                               // кінець ad_config_default

AdDecision ad_decide(const AdFrame* frame, const AdConfig* cfg, float overexp_ready) { // головне дерево рішення
  AdDecision best;              // сюди зберемо відповідь

  best.route = AD_ROUTE_NONE;   // спочатку: не чинимо
  best.health = 1.0f;           // спочатку повністю здоровий
  best.damage = 0.0f;           // спочатку пошкоджень немає
  best.repair_cost = 0.0f;      // ціни ремонту немає
  best.degrade.overexp = 0.0f;  // засвіт нуль

  if (frame == 0 || cfg == 0) { // немає кадра або налаштувань
    return best;                // безпечна відповідь
  }                             // кінець перевірки входу

  best.degrade.overexp = overexp_ready; // зберігаємо вимір засвіту (поки приходить ззовні)
  best.damage = overexp_ready;  // damage = overexp
  best.health = 1.0f - overexp_ready; // health = 1 - damage

  if (overexp_ready < cfg->overexp_tau) { // майже цілий кадр
    return best;                // НЕ чинимо (NONE)
  }                             // кінець гілки «здоровий»

  // кадр треба чіпати, але пріоритет далі буде у ДЕШЕВШИХ, не у «мега-вбитих»
  best.route = AD_ROUTE_DEOVER; // маршрут: зняття засвіту
  best.repair_cost = cfg->cost_base + cfg->cost_per_damage * overexp_ready; // ціна росте з силою засвіту
  return best;                  // віддаємо рішення (відбір найдешевших — у budget)
}                               // кінець ad_decide
