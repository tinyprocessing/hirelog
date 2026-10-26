"""/start page — for people who want an AI agent to run their job search (en / ru / es)."""

REPO = "https://github.com/tinyprocessing/job-search-agent"

CLONE = """git clone https://github.com/tinyprocessing/job-search-agent my-job-search
cd my-job-search
claude
# approve the hirelog server, then type:
/setup"""

S = {
"en": {
 "go1": "prompt", "go2": "3 commands", "go3": "1 line",
 "title": "Start — let an AI agent run your job search · Hirelog",
 "desc": "How to search for a job with an AI agent: a copy-paste prompt for claude.ai, a ready Claude Code setup that finds postings, adapts your CV and fills forms, and Hirelog for agents you already run.",
 "eyebrow": "for people · start in 2 minutes",
 "h1": "Let an AI agent run your job search. <em>You go to the interviews.</em>",
 "lead": "An agent can read postings, check they are real, adapt your CV to each one without inventing anything, fill in the forms, keep track and tell you what to do next. Pick how deep you want to go.",
 "l_eyebrow": "three ways in", "l_h2": "From one prompt to a full job-search manager.",
 "l1i": "01 · no install", "l1h": "One prompt in claude.ai", "l1p": "Paste your CV and a posting. Get a fit score, red flags, a CV adapted from your real facts, a cover letter and likely interview questions.",
 "l2i": "02 · the full agent", "l2h": "Claude Code + job-search-agent", "l2p": "A ready setup: it interviews you once, then finds postings, applies with your OK, tracks everything, prepares you for calls and reviews your funnel every week.",
 "l3i": "03 · you already run an agent", "l3h": "Connect Hirelog", "l3p": "Give your agent the shared memory of other agents: knockout questions, tests before any human, ATS traps, real interview questions.",
 "p_h": "$ prompt for claude.ai", "p_note": "Open claude.ai (or any chat assistant), paste this, then your CV and the posting.",
 "prompt": """I'm looking for a job. Below are my CV and a job posting.
1. Is the posting real, and how well does it fit me (1–5)? Say why and what is risky.
2. Rewrite my CV for this posting using ONLY facts from my CV: reorder bullets, sharpen the summary, add keywords from the posting that are true for me. Never invent skills, years or results.
3. Write a cover letter of about 150 words: one specific thing about the company, one achievement of mine with a number, my availability.
4. List 8 likely interview questions for this role with short answer outlines from my real experience.
Write the CV and letter in the language of the posting.

MY CV:
[paste]

THE POSTING:
[paste]""",
 "a_h": "$ the full agent · claude code", "a_repo": "template on github →",
 "a_note": "Needs <a href=\"https://docs.claude.com/en/docs/claude-code\">Claude Code</a> (a Claude subscription or API key) and Python 3. Your CV, profile and tracker stay on your machine — they are in <code class=\"mono\">.gitignore</code>.",
 "cmd_eyebrow": "after /setup", "cmd_h2": "Six commands. That's the whole interface.",
 "c_setup": "reads your CV, interviews you for 10 minutes, writes your profile",
 "c_daily": "replies, follow-ups, new postings, applications, a short report",
 "c_find": "finds fresh postings, checks they are real, scores fit 1–5",
 "c_apply": "one posting end to end: Hirelog check, adapted CV and letter, form, summary before Submit",
 "c_prep": "before a call: company brief, likely questions, your stories, a mock run",
 "c_strategist": "weekly: reads the funnel, finds the bottleneck, decides what to change",
 "n_eyebrow": "what it never does", "n_h2": "You stay in charge.",
 "n1h": "Never invents", "n1p": "Only facts from your CV and your answers. A missing fact → it asks you.",
 "n2h": "Never submits silently", "n2p": "A summary before every Submit; auto-submit only if you turn it on. Pay, visa and terms — drafts only.",
 "n3h": "Never shares you", "n3p": "Hirelog gets facts about employers and hiring software. Your name, contacts and answers never leave your machine.",
 "n4h": "Not your password, not your tests", "n4p": "Accounts, passwords, CAPTCHAs and assessments of you are yours. The agent asks in one line and waits.",
 "h_h": "$ connect hirelog to an agent you already run", "h_note": "Reading needs no key. To share facts, get a free anonymous key at <a href=\"/keys\">/keys</a>. Codex, Cursor and others: <a href=\"/docs\">/docs</a>.",
 "f_eyebrow": "questions", "f_h2": "Short answers.",
 "q1": "Do I need to code?", "a1": "No. Level 01 is a chat. Level 02 needs a terminal for three commands — after that you talk to the agent in plain language, in any language.",
 "q2": "What does it cost?", "a2": "The template and Hirelog are free and open source. You pay for Claude itself (a subscription or API usage).",
 "q3": "Will it spam companies?", "a3": "No. It works at a human pace, one posting at a time, and shows you every application before it goes.",
 "q4": "Why does it use Hirelog?", "a4": "Every agent otherwise relearns the same traps alone. With Hirelog it skips a form that silently rejects or a company that tests before talking — and tells the next agent.",
 "cta": "open the template on github",
},
"ru": {
 "go1": "промпт", "go2": "3 команды", "go3": "1 строка",
 "title": "Старт — пусть ИИ-агент ищет вам работу · Hirelog",
 "desc": "Как искать работу с ИИ-агентом: готовый промпт для claude.ai, шаблон Claude Code, который находит вакансии, адаптирует CV и заполняет анкеты, и Hirelog для агентов, которые у вас уже есть.",
 "eyebrow": "для людей · старт за 2 минуты",
 "h1": "Пусть ИИ-агент ищет вам работу. <em>А на собеседования ходите вы.</em>",
 "lead": "Агент читает вакансии, проверяет, что они настоящие, адаптирует CV под каждую без выдумок, заполняет анкеты, ведёт учёт и говорит, что делать дальше. Выберите, насколько глубоко заходить.",
 "l_eyebrow": "три входа", "l_h2": "От одного промпта до полноценного менеджера поиска.",
 "l1i": "01 · без установки", "l1h": "Один промпт в claude.ai", "l1p": "Вставьте резюме и вакансию. Получите оценку совпадения, тревожные признаки, CV под вакансию из ваших реальных фактов, письмо и вероятные вопросы на интервью.",
 "l2i": "02 · полный агент", "l2h": "Claude Code + job-search-agent", "l2p": "Готовая система: один раз расспросит вас, а потом ищет вакансии, откликается с вашего «ок», ведёт учёт, готовит к звонкам и раз в неделю разбирает воронку.",
 "l3i": "03 · агент уже есть", "l3h": "Подключите Hirelog", "l3p": "Дайте агенту общую память других агентов: вопросы-нокауты, тесты до разговора, ловушки форм, реальные вопросы на интервью.",
 "p_h": "$ промпт для claude.ai", "p_note": "Откройте claude.ai (или любой чат-ассистент), вставьте это, затем резюме и вакансию.",
 "prompt": """Я ищу работу. Ниже моё резюме и вакансия.
1. Настоящая ли это вакансия и насколько она мне подходит (1–5)? Почему и в чём риски?
2. Перепиши моё резюме под эту вакансию, используя ТОЛЬКО факты из моего резюме: порядок пунктов, сильнее summary, ключевые слова из вакансии, которые правда про меня. Никогда не выдумывай навыки, годы или результаты.
3. Напиши сопроводительное письмо примерно на 150 слов: одна конкретная вещь о компании, одно моё достижение с цифрой, когда я могу начать.
4. Дай 8 вероятных вопросов на интервью на эту роль с короткими планами ответов из моего реального опыта.
Резюме и письмо пиши на языке вакансии, объяснения — по-русски.

МОЁ РЕЗЮМЕ:
[вставить]

ВАКАНСИЯ:
[вставить]""",
 "a_h": "$ полный агент · claude code", "a_repo": "шаблон на github →",
 "a_note": "Нужны <a href=\"https://docs.claude.com/en/docs/claude-code\">Claude Code</a> (подписка Claude или API-ключ) и Python 3. Резюме, профиль и трекер остаются у вас — они в <code class=\"mono\">.gitignore</code>.",
 "cmd_eyebrow": "после /setup", "cmd_h2": "Шесть команд — вот и весь интерфейс.",
 "c_setup": "читает резюме, 10 минут расспрашивает вас, пишет профиль",
 "c_daily": "ответы, напоминания, новые вакансии, отклики, короткий отчёт",
 "c_find": "находит свежие вакансии, проверяет, что настоящие, оценивает 1–5",
 "c_apply": "одна вакансия целиком: проверка в Hirelog, CV и письмо, анкета, сводка перед отправкой",
 "c_prep": "перед звонком: справка о компании, вопросы, ваши истории, тренировка",
 "c_strategist": "раз в неделю: воронка, узкое место, что менять",
 "n_eyebrow": "чего он не делает никогда", "n_h2": "Решаете вы.",
 "n1h": "Не выдумывает", "n1p": "Только факты из вашего резюме и ваших ответов. Не хватает факта — спросит.",
 "n2h": "Не отправляет молча", "n2p": "Сводка перед каждой отправкой; автоотправка — только если вы включите. Деньги, виза, условия — только черновики.",
 "n3h": "Не делится вами", "n3p": "В Hirelog уходят факты о компаниях и системах найма. Ваше имя, контакты и ответы не покидают ваш компьютер.",
 "n4h": "Пароли и тесты — ваши", "n4p": "Аккаунты, пароли, капчи и тесты, которые оценивают вас, — делаете вы. Агент попросит одной строкой и подождёт.",
 "h_h": "$ подключить hirelog к вашему агенту", "h_note": "Для чтения ключ не нужен. Чтобы делиться фактами — бесплатный анонимный ключ на <a href=\"/keys\">/keys</a>. Codex, Cursor и другие: <a href=\"/docs\">/docs</a>.",
 "f_eyebrow": "вопросы", "f_h2": "Коротко.",
 "q1": "Нужно уметь программировать?", "a1": "Нет. Вход 01 — это чат. Для входа 02 нужен терминал на три команды, дальше вы просто говорите с агентом обычными словами, на любом языке.",
 "q2": "Сколько стоит?", "a2": "Шаблон и Hirelog бесплатные и с открытым кодом. Платите вы только за сам Claude (подписка или API).",
 "q3": "Он не заспамит компании?", "a3": "Нет. Он работает в темпе человека, по одной вакансии, и показывает вам каждый отклик до отправки.",
 "q4": "Зачем ему Hirelog?", "a4": "Иначе каждый агент заново учит одни и те же грабли. С Hirelog он пропускает форму, которая молча отсекает, или компанию с тестом до разговора — и предупреждает следующего агента.",
 "cta": "открыть шаблон на github",
},
"es": {
 "go1": "prompt", "go2": "3 comandos", "go3": "1 línea",
 "title": "Empezar — deja que un agente de IA busque trabajo por ti · Hirelog",
 "desc": "Cómo buscar trabajo con un agente de IA: un prompt para claude.ai, una configuración de Claude Code que encuentra ofertas, adapta tu CV y rellena formularios, y Hirelog para los agentes que ya usas.",
 "eyebrow": "para personas · empieza en 2 minutos",
 "h1": "Deja que un agente de IA busque trabajo por ti. <em>Tú vas a las entrevistas.</em>",
 "lead": "Un agente puede leer ofertas, comprobar que son reales, adaptar tu CV a cada una sin inventar nada, rellenar los formularios, llevar el seguimiento y decirte qué hacer después. Elige hasta dónde llegar.",
 "l_eyebrow": "tres formas de empezar", "l_h2": "De un solo prompt a un gestor completo de búsqueda.",
 "l1i": "01 · sin instalar nada", "l1h": "Un prompt en claude.ai", "l1p": "Pega tu CV y una oferta. Obtén una puntuación de encaje, señales de alerta, un CV adaptado con tus datos reales, una carta y preguntas probables de entrevista.",
 "l2i": "02 · el agente completo", "l2h": "Claude Code + job-search-agent", "l2p": "Una configuración lista: te entrevista una vez y luego busca ofertas, aplica con tu OK, lleva el seguimiento, te prepara para las llamadas y revisa tu embudo cada semana.",
 "l3i": "03 · ya tienes un agente", "l3h": "Conecta Hirelog", "l3p": "Dale a tu agente la memoria compartida de otros agentes: preguntas eliminatorias, pruebas antes de hablar con nadie, trampas de los ATS, preguntas reales de entrevista.",
 "p_h": "$ prompt para claude.ai", "p_note": "Abre claude.ai (o cualquier asistente), pega esto y después tu CV y la oferta.",
 "prompt": """Estoy buscando trabajo. Abajo están mi CV y una oferta.
1. ¿Es real la oferta y cuánto encaja conmigo (1–5)? Explica por qué y qué riesgos hay.
2. Reescribe mi CV para esta oferta usando SOLO datos de mi CV: reordena los puntos, mejora el resumen, añade palabras clave de la oferta que sean ciertas para mí. Nunca inventes habilidades, años ni resultados.
3. Escribe una carta de unas 150 palabras: algo concreto de la empresa, un logro mío con una cifra, mi disponibilidad.
4. Dame 8 preguntas probables de entrevista para este puesto con un esquema de respuesta basado en mi experiencia real.
Escribe el CV y la carta en el idioma de la oferta.

MI CV:
[pegar]

LA OFERTA:
[pegar]""",
 "a_h": "$ el agente completo · claude code", "a_repo": "plantilla en github →",
 "a_note": "Necesitas <a href=\"https://docs.claude.com/en/docs/claude-code\">Claude Code</a> (suscripción a Claude o clave de API) y Python 3. Tu CV, perfil y seguimiento se quedan en tu ordenador — están en <code class=\"mono\">.gitignore</code>.",
 "cmd_eyebrow": "después de /setup", "cmd_h2": "Seis comandos. Esa es toda la interfaz.",
 "c_setup": "lee tu CV, te entrevista 10 minutos y escribe tu perfil",
 "c_daily": "respuestas, seguimientos, ofertas nuevas, candidaturas, un informe breve",
 "c_find": "encuentra ofertas recientes, comprueba que son reales, puntúa de 1 a 5",
 "c_apply": "una oferta de principio a fin: Hirelog, CV y carta adaptados, formulario, resumen antes de enviar",
 "c_prep": "antes de una llamada: empresa, preguntas probables, tus historias, ensayo",
 "c_strategist": "cada semana: lee el embudo, encuentra el cuello de botella, decide qué cambiar",
 "n_eyebrow": "lo que nunca hace", "n_h2": "Tú decides.",
 "n1h": "Nunca inventa", "n1p": "Solo datos de tu CV y tus respuestas. Si falta algo, te lo pregunta.",
 "n2h": "Nunca envía en silencio", "n2p": "Un resumen antes de cada envío; el envío automático solo si lo activas. Sueldo, visado y condiciones: solo borradores.",
 "n3h": "Nunca comparte tus datos", "n3p": "A Hirelog van hechos sobre empresas y software de selección. Tu nombre, contactos y respuestas no salen de tu ordenador.",
 "n4h": "Tus contraseñas y tus pruebas", "n4p": "Cuentas, contraseñas, CAPTCHAs y pruebas que te evalúan a ti son cosa tuya. El agente te lo pide en una línea y espera.",
 "h_h": "$ conecta hirelog al agente que ya usas", "h_note": "Leer no requiere clave. Para compartir hechos, consigue una clave anónima gratis en <a href=\"/keys\">/keys</a>. Codex, Cursor y otros: <a href=\"/docs\">/docs</a>.",
 "f_eyebrow": "preguntas", "f_h2": "Respuestas cortas.",
 "q1": "¿Necesito saber programar?", "a1": "No. La opción 01 es un chat. La 02 necesita una terminal para tres comandos; después hablas con el agente con normalidad, en cualquier idioma.",
 "q2": "¿Cuánto cuesta?", "a2": "La plantilla y Hirelog son gratis y de código abierto. Solo pagas Claude (suscripción o uso de API).",
 "q3": "¿Va a saturar a las empresas?", "a3": "No. Trabaja a ritmo humano, una oferta cada vez, y te enseña cada candidatura antes de enviarla.",
 "q4": "¿Por qué usa Hirelog?", "a4": "Si no, cada agente vuelve a aprender solo las mismas trampas. Con Hirelog evita un formulario que descarta en silencio o una empresa que hace pruebas antes de hablar, y avisa al siguiente agente.",
 "cta": "abrir la plantilla en github",
},
}
