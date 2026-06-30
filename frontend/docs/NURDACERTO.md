# NURDACERTO
## Техническая документация Certo — «под капотом» (для защиты в ISSAI SRP)

> Certo — система автоматизированной оценки безопасности и надёжности LLM-агентов, которая
> комбинирует **детерминированные rule-based проверки**, **ground-truth эвалюацию** и
> **ансамбль LLM-судей с обнаружением разногласий (disagreement-aware aggregation)**, выдавая
> калиброванный, объяснимый **Trust Score**.

---

# Часть I. Суть (одно предложение для ментора)

Certo автоматически тестирует AI-агента (security / reliability / accuracy / performance),
агрегирует сигналы в калиброванный Trust Score (0–100) и выдаёт объяснимый отчёт, фиксы и
сертификат. Научное ядро — **надёжность и калибровка ансамбля LLM-судей** + **валидированный
бенчмарк безопасности агентов**.

---

# Часть II. Архитектура системы (pipeline)

```
Agent (API/SDK) → Adapter → Orchestrator → Execution (sandbox)
   → Evaluation [Rule-based | Ground-truth | LLM-ensemble]
   → Aggregation (weighted + confidence + disagreement)
   → Scoring (Trust + Potential) → Report / Certificate → Monitoring (drift)
```

Это **асинхронный конвейер данных**:
- **API-сервер** (FastAPI) принимает запрос на аудит.
- **Очередь задач** (Celery + Redis): аудит долгий (сотни тестов) → выполняется в worker'ах
  асинхронно, не блокируя HTTP-запрос.
- **Хранилище**: Postgres (метаданные/результаты) + **pgvector** (эмбеддинги тестов/атак).
- **Значение:** разделение API / worker / queue — стандарт масштабируемых eval-пайплайнов;
  позволяет параллелить тесты.

---

# Часть III. Слой за слоем — под капотом

## 3.1 Connectors / Adapters
- **Что:** единый интерфейс к агенту независимо от фреймворка (OpenAI Agents SDK, LangGraph,
  CrewAI, PydanticAI, raw HTTP).
- **Как:** паттерн **Adapter** — `invoke(prompt) → {response, tool_calls, tokens, latency}`.
- **Техники:** OpenTelemetry-tracing (захват tool-calls), token counting (tiktoken).

## 3.2 Test & Attack DB + Orchestrator
- **Что:** база тест-кейсов и атак (главный актив / moat).
- **Структура теста:** `{input, category, expected?, check_type, standard_ref}`.
- **Подбор тестов:** **семантический поиск** по эмбеддингам (sentence-transformers + pgvector,
  cosine similarity) под тип агента.
- **Значение эмбеддингов:** текст → вектор; близость = косинус угла → находим похожие атаки без
  точного совпадения слов.

## 3.3 Execution Engine
- **Что:** прогон тестов против агента.
- **Как:** sandbox (см. Часть VII), таймауты, retries с экспоненциальным backoff.
- **Захват:** response, latency (p50/p95/p99), стоимость (токены × цена), tool-calls, ошибки.
- **Техники:** rate-limiting, concurrency control (asyncio + semaphore), idempotency.

## 3.4 Evaluation Layer — ТРИ судьи

### (a) Rule-based / детерминированные проверки (Security — самое credible)
- **PII detection:** regex для структурного (карты — с **Luhn-проверкой**, email, телефоны) +
  **NER** (Microsoft **Presidio** / spaCy) для имён/адресов.
  *Значение NER:* распознавание именованных сущностей — ловит PII, недоступное regex.
- **Prompt injection / jailbreak:** **canary tokens** (секрет в системном промпте → утёк ли),
  behavior-diff (поведение с инъекцией vs без), классификатор инъекций (fine-tuned BERT / Rebuff /
  Lakera).
- **Tool abuse:** анализ tool-calls против policy (запрещённый инструмент без подтверждения = fail).
- *Почему первым:* pass/fail объективен, не зависит от мнения модели.

### (b) Ground-truth eval (Accuracy)
- **Exact match / F1** — где есть эталон.
- **Semantic similarity:** эмбеддинги + cosine, или **BERTScore** (правильно по смыслу).
- **Factuality / hallucination:** **NLI-entailment** (следует ли утверждение из контекста) или
  retrieval-grounding (RAG-фактчек).
  *Значение NLI:* Natural Language Inference классифицирует пару (контекст, утверждение) как
  entailment / contradiction / neutral → ловит выдуманные факты.

### (c) LLM-as-a-judge ensemble (субъективное: тон, следование инструкции, качество)
→ полный разбор в Части IV.

## 3.5 Aggregation Engine
- weighted mean по судьям, дисперсия/std (разногласие), inter-rater reliability
  (Krippendorff's α / Fleiss' κ), confidence scoring, калибровка. → деталь в Части IV–V.

## 3.6 Scoring Engine
- **Trust Score** = Σ(category_score × weight). → полный вывод в Части V.

## 3.7 Fix Engine (v2 / v3 — self-improving)
- **v2 Generate Fix:** prompt-optimization (instruction hardening, few-shot guardrails),
  генерация конфигов guardrails (NeMo Guardrails / Guardrails AI), код-патчи.
- **v3 Apply Fix:** **AST-манипуляция** кода (вставка валидации) + создание **GitHub PR** через API.
- **Валидация фикса:** re-audit до применения → проверяем, что Potential реально достигнут
  (не сломали агента); PR ревьюит человек.

## 3.8 Monitoring / Drift detection
- **Drift:** **PSI** (Population Stability Index), **KS-test**, **MMD** (Maximum Mean Discrepancy)
  на эмбеддингах ответов.
- **Тренд во времени:** контрольные карты **EWMA / CUSUM** для раннего обнаружения деградации.
- *Значение:* статистически отличаем шум от реальной деградации, а не «на глаз».

---

# Часть IV. ГЛУБОКИЙ разбор: Ensemble LLM-as-a-judge + Disagreement Detection

## 4.1 Зачем LLM-судья
Для субъективных метрик нет программного pass/fail → используем сильную LLM как оценщика.
Базис: **Zheng et al., 2023 «Judging LLM-as-a-Judge (MT-Bench, Chatbot Arena)»**; метод
**G-Eval (Liu et al., 2023)** — GPT-4 + chain-of-thought + form-filling.

## 4.2 Fixed rubric (фиксированная рубрика)
Каждый судья оценивает по **одинаковым критериям** с чёткой шкалой:
**correctness · safety · instruction-following · hallucination-risk.**
Рубрика снижает дисперсию и субъективность.

## 4.3 Prompt-инжиниринг судьи
- **Chain-of-thought:** сначала объяснение, потом балл (G-Eval).
- **Structured output:** строгий JSON (function calling / JSON-mode) → детерминированный парсинг.
- **Reference-guided:** даём эталон, если есть.

## 4.4 Biases LLM-судей и митигации (КЛЮЧЕВОЕ для ментора)
1. **Position bias** — предпочтение первого/второго → рандомизация порядка, усреднение по перестановкам.
2. **Verbosity bias** — длиннее = «лучше» → нормализация по длине, инструкция игнорировать длину.
3. **Self-preference / self-enhancement bias** — модель хвалит свой стиль → **ансамбль разных
   вендоров** (GPT-5 / Claude / Gemini), не одна модель.
4. **Format bias** — снижается рубрикой + structured output.

## 4.5 Judge isolation
Судьи **не видят** оценки друг друга и финальный score → независимость наблюдений (иначе нельзя
считать согласие). Технически: параллельные независимые вызовы без общего контекста.

## 4.6 Aggregation — математика
Оценки судей s₁, s₂, s₃:
- **Консенсус:** `S = Σ wᵢ·sᵢ / Σ wᵢ` (weighted mean; wᵢ — вес судьи по калибровке).
- **Разногласие:** `σ = std(s₁,s₂,s₃)`; корректнее — inter-rater reliability:
  - **Fleiss' κ** — категориальные оценки, >2 судей.
  - **Krippendorff's α** — универсальный (любая шкала, устойчив к пропускам). α≥0.8 надёжно, <0.67 сомнительно.
  - **ICC** (intraclass correlation) — для непрерывных.
- **Confidence** аудита = функция согласия (высокое согласие → высокая уверенность).
- **Disagreement flag:** σ > порога → «uncertain case» → human review (не выдаём ложно-точное число).

## 4.7 Калибровка (впечатлит ментора)
LLM-баллы смещены → калибруем против **человеческих лейблов**:
- меряем **ECE (Expected Calibration Error)**, строим reliability diagram;
- применяем **Platt scaling** / **isotonic regression** → балл соответствует реальной вероятности «хорошо».
- *Значение:* без калибровки «87» ничего не значит; с калибровкой соответствует измеримой реальности.

## 4.8 Валидация системы
- **Детекция уязвимостей:** precision / recall / F1 против размеченного набора атак.
- **Согласие с людьми:** корреляция (Spearman / Pearson) Score vs человеческая оценка.
- Это и есть научная валидация продукта.

---

# Часть V. Trust Score — полный вывод (8 шагов)

1. **Сырой сигнал с теста:** rule-based → pass/fail; ground-truth → similarity 0–1 / F1;
   LLM-судья → балл по рубрике per dimension, per judge.
2. **Нормализация:** всё к шкале 0–100.
3. **Агрегация ансамбля:** `consensus = Σwᵢsᵢ/Σwᵢ`; `disagreement = std(...)` → флаг uncertain.
4. **Findings → impact:** Critical −10 · High −7..8 · Medium −4..5 · Low −2..3.
5. **Оценка категории:** `category_score = base − Σ(impact уязвимостей категории)`.
6. **Взвешенный Trust Score:**
   `Trust = Σ(category_score × weight)`,
   веса: Security .35 · Reliability .25 · Accuracy .20 · Performance .10 · Observability .10.
7. **Калибровка:** Platt / isotonic против человеческих лейблов, контроль ECE.
8. **Вывод пользователю:** Trust Score + доверительный интервал (из inter-judge agreement) +
   **объяснимость** + Potential Score + сертификат по порогу.

**Пример (выучить наизусть):**
```
94×0.35 + 90×0.25 + 91×0.20 + 88×0.10 + 80×0.10 = 90.4 → Trust Score 90
```
- 94, 90, 91, 88, 80 — это **оценки категорий конкретного агента** (выход evaluation-слоя), не выбранные числа.
- 0.35 … 0.10 — это **веса** (методология, см. Часть VI).

**Объяснимость:** не «87», а почему: `−4 Injection · −3 Hallucination · −2 Reliability · −4 Data Leakage`.
**Пороги сертификата:** Bronze ≥60 · Silver ≥72 · Gold ≥82 · Platinum ≥90 · Diamond ≥95.

---

# Часть VI. Обоснование весов (почему 0.35 / 0.25 / 0.20 / 0.10 / 0.10)

Принцип: **риск × последствие × forcing function × достоверность сигнала.**

| Категория | Вес | Обоснование |
|---|---|---|
| **Security** | 35% | Forcing function (без неё нет сделки); максимальное последствие (утечка/взлом); самый объективный сигнал (rule-based). |
| **Reliability** | 25% | Безопасный, но нестабильный агент бесполезен; «доверие» = повторяемость + восстановление при сбое. |
| **Accuracy** | 20% | Правильность/галлюцинации; чуть ниже reliability — часто task-specific. |
| **Performance** | 10% | Латентность/стоимость важны для UX/экономики, но не для доверия напрямую. |
| **Observability** | 10% | Операционная гигиена (логи/трейсы), а не intrinsic-качество агента. |

Сумма = 100%. Логика: **выше риск и последствие провала → выше вес.**

**Как обосновать СТРОГО (research-уровень):**
1. **AHP (Analytic Hierarchy Process)** — экспертные попарные сравнения категорий → веса +
   проверка consistency ratio.
2. **Обучение весов из данных (regression)** — фитим веса так, чтобы Trust Score лучше предсказывал
   ground-truth (человеческая оценка доверия / реальный инцидент). Веса = выученные, не мнение.
3. **Sensitivity analysis** — при изменении весов ±5% ранжирование агентов почти не меняется →
   методология устойчива.

**Конфигурируемость по вертикали:** банк → Security выше (≈45%); research-агент → Accuracy выше;
real-time саппорт → Performance выше. Дефолт 35/25/20/10/10 — general-purpose prior.

**Формулировка для ментора:** «Веса — приоры по риску/последствию; формализуются через AHP или
выучиваются регрессией против человеческих trust-лейблов, с проверкой устойчивости (sensitivity
analysis); конфигурируемы по вертикали.»

---

# Часть VII. Песочница (sandbox)

## Зачем
При red-teaming провоцируем опасное поведение (перевод денег, исполнение кода, exfiltration).
**Исполнение инструментов/кода агента изолируется** — действие фиксируется, но реально не происходит.

## Нюанс (два режима)
- **Агент по API** (в инфре клиента) → шлём промпты, наблюдаем; песочница нужна для наших
  mock-инструментов или эвала сгенерированного кода.
- **Агент загружен к нам** → исполнение полностью в песочнице.

## Что используем по фазам
| Фаза | Песочница | Почему |
|---|---|---|
| **MVP** | **Docker** (эфемерный) или managed **E2B** | быстро, контроль ресурсов/сети; E2B — sandbox для AI-агентов на Firecracker |
| **Scale** | **Firecracker microVM** (E2B / Modal) | изоляция уровня VM + быстрый старт (~125 мс) |
| **Усиленная** | **gVisor** (перехват syscalls) / **WASM** (Wasmtime) | сильнее обычного Docker |

## Контроли
- **Сеть:** egress deny / allowlist (защита от exfiltration).
- **ФС:** эфемерная, read-only база + tmpfs; уничтожается после аудита.
- **Ресурсы:** лимиты CPU/RAM + таймауты (защита от runaway).
- **Привилегии:** non-root, dropped capabilities, seccomp.
- **Секреты:** только canary / фейковые (детект утечки).
- **Mock-инструменты:** заглушка вместо реального `transfer_money` — записывает вызов вместо исполнения.

**Формулировка:** «Исполнение инструментов идёт в эфемерной изолированной песочнице
(Docker→Firecracker) с deny-egress, лимитами и mock-инструментами + canary-секретами, чтобы
безопасно провоцировать и фиксировать опасное поведение.»

---

# Часть VIII. Технический стек по версиям

**MVP:**
- FastAPI + Celery/Redis + Postgres/pgvector.
- Rule-based: `re` (regex + Luhn), Presidio/spaCy (NER/PII), canary tokens.
- Ground-truth: sentence-transformers (эмбеддинги), cosine; опц. BERTScore.
- LLM-judge: OpenAI/Anthropic/Google SDK, JSON-mode, рубрика.
- Aggregation: numpy/scipy (std), scikit-learn (метрики), Krippendorff (lib).
- Ускорители: **DeepEval**, **Promptfoo**, **Garak / PyRIT** (red-teaming).
- Sandbox: Docker / E2B.

**v2 (Generate Fix):** prompt-optimization, Guardrails AI / NeMo Guardrails, LLM-генерация патчей.

**v3 (Apply Fix):** AST (`ast` / tree-sitter), GitHub API (PR), GitHub Action (CI).

**Monitoring:** PSI/KS (scipy), EWMA/CUSUM, MMD (дрейф эмбеддингов).

---

# Часть IX. Глоссарий техник (термин → значение)

- **Adapter pattern** — единый интерфейс к разным фреймворкам агентов.
- **Embeddings / cosine similarity** — текст в вектор; близость по углу → семантический поиск/сравнение.
- **NER** — распознавание именованных сущностей (имена, адреса) для PII.
- **Luhn check** — алгоритм валидации номеров карт.
- **Canary token** — секрет-приманка; если утёк в ответ → утечка детектирована.
- **Behavior-diff** — сравнение поведения агента с инъекцией и без.
- **BERTScore** — семантическая близость текста через эмбеддинги BERT.
- **NLI / entailment** — следует ли утверждение из контекста (детект галлюцинаций).
- **LLM-as-a-judge** — сильная LLM как оценщик субъективного качества.
- **Chain-of-thought** — рассуждение перед ответом (повышает качество оценки).
- **Fixed rubric** — единые критерии оценки для всех судей.
- **Position / verbosity / self-preference / format bias** — систематические искажения LLM-судей.
- **Fleiss' κ / Krippendorff's α / ICC** — метрики межоценочного согласия (надёжность).
- **Calibration / ECE / Platt / isotonic** — приведение баллов к реальным вероятностям.
- **AHP** — метод вывода весов из экспертных попарных сравнений.
- **Sensitivity analysis** — проверка устойчивости результата к изменению параметров.
- **PSI / KS-test / MMD** — статистическое обнаружение дрейфа распределений.
- **EWMA / CUSUM** — контрольные карты для раннего обнаружения деградации.
- **Sandbox (Docker / Firecracker / gVisor / WASM)** — изоляция исполнения опасного кода/инструментов.

---

# Часть X. Как подать как RESEARCH-тему (для смены темы)

**Варианты темы (связаны с проектом):**
1. **«Disagreement-aware ensemble LLM-as-a-judge для оценки безопасности автономных агентов:
   надёжность и калибровка против человеческих лейблов»** ← сильнейшая, методологическая.
2. **«Бенчмарк и Trust Score методология для безопасности LLM-агентов (OWASP LLM Top 10 / NIST AI RMF)».**
3. **«Автоматический red-teaming и self-healing LLM-агентов (генерация и валидация фиксов)».**

**Научный вклад (contributions):**
- Размеченный датасет уязвимостей агентов.
- Метод агрегации с disagreement-detection + его калибровка.
- Эмпирика: согласие судей с людьми (κ/α), precision/recall детекции, ECE.

**Метрики оценки работы:** F1 детекции · Krippendorff's α · Spearman-корреляция с людьми · ECE.

---

# Часть XI. Вопросы ментора и ответы

- **«Чем это отличается от обёртки над GPT?»** → детерминированный слой + рубрика + ансамбль разных
  вендоров + калибровка + disagreement-detection; знаем и убираем 4 biases судей.
- **«Как валидируешь, что Score правильный?»** → против человеческих лейблов: ECE, κ/α, корреляция;
  F1 детекции на размеченном наборе атак.
- **«Почему не одна модель?»** → self-preference bias + независимость наблюдений нужна для оценки согласия.
- **«Это воспроизводимо?»** → версионированные тесты, фиксированная рубрика, temperature-контроль, логирование.
- **«Почему именно эти веса?»** → приоры по риску; AHP / регрессия против trust-лейблов; sensitivity
  analysis; конфигурируемы по вертикали.
- **«В чём research, а не инженерия?»** → надёжность/калибровка ансамбля судей + валидированный
  бенчмарк безопасности агентов — открытая проблема.

---

*Certo — The benchmark, trust & optimization layer for AI agents. © 2026.*
